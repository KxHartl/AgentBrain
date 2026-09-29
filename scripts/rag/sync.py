"""
LiteRealm RAG — incremental sync of data/sources/ into the vector store.

Unlike `ingest` (full rebuild of the top-level PDFs), sync walks data/sources/**
recursively, hashes every PDF and only parses + embeds files that are new or changed
since the last sync. State lives in <store dir>/sync_state.json.

    rag.sh sync                 # index new/changed PDFs (Docling)
    rag.sh sync --fast          # pypdf instead of Docling (quick, no layout)
    rag.sh sync --dry-run       # show the plan, change nothing
    rag.sh sync --full          # re-index everything (e.g. after changing the embedding model)
    rag.sh sync --prune         # Qdrant: also delete points of removed/changed files

Backends (store_adapter.get_vector_store): Qdrant when QDRANT_URL answers, else LanceDB.
LanceDB is per project, so changed/removed files are always replaced there. The Qdrant
collection is shared: points are tagged with `project`, and deletions (--prune) only
ever touch points carrying this project's tag. Without --prune a changed file's old
chunks stay until pruned (upserts are idempotent, so unchanged chunks are not duplicated).

The chunk `domain` is the first folder under data/sources/ (standards/, papers/, ...),
or "general" for top-level files.

Rebuilt 2026-09 from the interface the LiteRealm rag helper calls (`rag sync`); the
original was lost with the work disk (see RECOVERY.md).
"""

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rag_paths import enable_utf8_io, resolve_store_dir  # noqa: E402

STATE_NAME = "sync_state.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def domain_of(rel):
    parts = Path(rel).parts
    return parts[0] if len(parts) > 1 else "general"


def scan(sources):
    return {p.relative_to(sources).as_posix(): p for p in sorted(sources.rglob("*.pdf")) if p.is_file()}


def load_state(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  {path.name} unreadable - treating as a first sync.")
    return {}


def plan(files, state, full):
    known = {} if full else state.get("files", {})
    new, changed, unchanged = [], [], []
    hashes = {}
    for rel, path in files.items():
        hashes[rel] = sha256(path)
        if rel not in known:
            new.append(rel)
        elif known[rel].get("sha256") != hashes[rel]:
            changed.append(rel)
        else:
            unchanged.append(rel)
    removed = sorted(set(state.get("files", {})) - set(files))
    return new, changed, unchanged, removed, hashes


def parse(paths, fast, ocr, sources):
    import ingest as base
    if fast:
        chunks = []
        for p in paths:
            print(f"  Parsing: {p.name} (pypdf)...")
            chunks.extend(base._fallback_parse(p))
        return chunks
    return base.parse_with_docling(sources, enable_ocr=ocr, pdf_files=paths)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Incremental RAG sync of data/sources/**.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--fast", action="store_true", help="pypdf parsing instead of Docling")
    parser.add_argument("--ocr", action="store_true", help="full-page OCR for scanned PDFs (Docling)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan only")
    parser.add_argument("--full", action="store_true", help="re-index every file")
    parser.add_argument("--prune", action="store_true",
                        help="Qdrant: delete this project's points of changed/removed files")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    os.chdir(root)  # store_adapter/ingest resolve the project from the cwd
    sources = root / "data" / "sources"
    if not sources.is_dir():
        print(f"No sources directory at {sources}")
        return 1

    from store_adapter import QdrantStore, get_vector_store
    store = get_vector_store(root)
    is_qdrant = isinstance(store, QdrantStore)
    backend = f"qdrant:{store.collection}" if is_qdrant else "lancedb"
    state_dir = resolve_store_dir(root / ".ai" / "rag" / "db", project_root=root)
    state_path = state_dir / STATE_NAME
    state = load_state(state_path)

    full = args.full
    if state and state.get("backend") != backend:
        print(f"  Backend changed ({state.get('backend')} -> {backend}): full sync.")
        full = True
    if not state and not is_qdrant:
        full = True  # no record of what the LanceDB table holds (e.g. built by `rag ingest`)

    files = scan(sources)
    new, changed, unchanged, removed, hashes = plan(files, state, full)
    names = collections.Counter(Path(r).name for r in files)
    dupes = sorted(n for n, c in names.items() if c > 1)
    if dupes:
        print(f"  WARNING: same file name in several folders (cite keys map by name): {', '.join(dupes)}")

    print(f"Sync plan ({backend}{', full' if full else ''}): {len(new)} new, {len(changed)} changed, "
          f"{len(removed)} removed, {len(unchanged)} unchanged")
    for label, items in (("new", new), ("changed", changed), ("removed", removed)):
        for rel in items:
            print(f"  {label:<8} {rel}")
    if args.dry_run:
        return 0
    todo = new + changed
    if not todo and not removed and not full:
        print("Nothing to do.")
        return 0

    import ingest as base
    project = root.name
    embed_fn = dim = model_id = None
    if todo:
        embed_fn, dim, model_id = base.load_embeddings()
        if state.get("model_id") and state["model_id"] != model_id and not full:
            print(f"Embedding model changed ({state['model_id']} -> {model_id}); "
                  f"vectors would not be comparable. Run: rag sync --full")
            return 1

    # Remove what is gone or about to be replaced.
    stale = [Path(r).name for r in changed + removed]
    if is_qdrant:
        if args.prune and stale:
            store.delete_sources(stale, project)
            print(f"  Pruned this project's points for {len(stale)} file(s).")
        elif stale:
            print(f"  {len(stale)} changed/removed file(s) keep their old points; --prune removes them.")
    elif full:
        store.drop()
    elif stale:
        store.delete_sources(stale)

    files_state = {} if full else dict(state.get("files", {}))
    for rel in removed:
        files_state.pop(rel, None)

    total = 0
    for rel in todo:
        chunks = parse([files[rel]], args.fast, args.ocr, sources)
        if not chunks:
            print(f"  {rel}: no text extracted - skipped (scanned? try --ocr)")
            continue
        vectors = []
        texts = [c["text"] for c in chunks]
        for i in range(0, len(texts), 64):
            vectors.extend(embed_fn(texts[i:i + 64]))
        domain = domain_of(rel)
        if is_qdrant:
            for c, v in zip(chunks, vectors):
                c["vector"], c["domain"] = v, domain
            n = store.upsert_chunks(chunks, model_id=model_id, dim=dim, scope="local",
                                    domain=domain, project=project)
        else:
            # Same schema as `rag ingest`, so query.py reads both.
            n = store.append_chunks([{"text": c["text"], "source_file": c["source_file"],
                                      "page": c["page"], "headings": c.get("headings", ""),
                                      "vector": v} for c, v in zip(chunks, vectors)])
        files_state[rel] = {"sha256": hashes[rel], "chunks": n, "domain": domain}
        total += n
        print(f"  indexed  {rel}  ({n} chunks, domain {domain})")

    state_dir.mkdir(parents=True, exist_ok=True)
    new_state = {"backend": backend, "model_id": model_id or state.get("model_id"),
                 "dim": dim or state.get("dim"), "updated": dt.datetime.now().isoformat(timespec="seconds"),
                 "files": files_state}
    state_path.write_text(json.dumps(new_state, indent=2, ensure_ascii=False), encoding="utf-8")
    if not is_qdrant and new_state["model_id"]:
        (state_dir / "embedding_meta.json").write_text(
            json.dumps({"model": new_state["model_id"], "dim": new_state["dim"], "table": "project_docs"},
                       indent=2), encoding="utf-8")
    print(f"Done. {total} chunk(s) from {len(todo)} file(s); {len(files_state)} file(s) tracked in {state_path}")
    return 0


if __name__ == "__main__":
    enable_utf8_io()
    import ingest as _base  # noqa: E402
    _base.ensure_brain_venv()
    sys.exit(main())
