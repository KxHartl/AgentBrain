"""The shared corpus: search, status and ingest, server first, local mirror second.

The main corpus lives in Qdrant (`QDRANT_URL`, `QDRANT_COLLECTION`). Queries and new
chunks are embedded here, on this machine, with the Ollama model that built the
collection (`OLLAMA_EMBED_MODEL`); the server only stores vectors. When Qdrant cannot be
reached, search falls back to the local mirror that `sync.py` keeps -- the same vectors,
so the same results, never a different embedding model.

Used by `mcp_server.py`; importable on its own:

    from corpus import search, status
    hits = search("question", k=5, source="file.pdf")
"""

import contextlib
import json
import os
import sys
import time
import urllib.error
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from store_adapter import (DEFAULT_COLLECTION, QdrantStore, _http, load_env,  # noqa: E402
                           ollama_embed, ollama_model)

MIRROR_TABLE = "corpus"
PAYLOAD_FIELDS = ("text", "source_file", "page", "headings", "domain", "project")


class CorpusError(RuntimeError):
    """A failure the caller should show as-is (unreachable store, model mismatch...)."""


def brain_dir():
    return Path(os.environ.get("AGENTBRAIN_PATH") or Path.home() / ".agentbrain")


def collection():
    return os.environ.get("QDRANT_COLLECTION", DEFAULT_COLLECTION)


def mirror_dir():
    """Where `sync.py` keeps the local copy of the collection."""
    override = os.environ.get("RAG_MIRROR_DIR")
    return Path(override) if override else brain_dir() / "rag" / "mirror" / collection()


def configure(root=None):
    """Load `.env` from `root` (a project), then from the brain; the environment wins."""
    if root:
        load_env(root)
    load_env(brain_dir())


def qdrant():
    """The configured QdrantStore, or None when `QDRANT_URL` is unset."""
    url = os.environ.get("QDRANT_URL")
    if not url:
        return None
    return QdrantStore(url, collection(), float(os.environ.get("QDRANT_TIMEOUT", "60")))


def _filter(source=None, domain=None, project=None):
    must = [{"key": k, "match": {"value": v}}
            for k, v in (("source_file", source), ("domain", domain), ("project", project)) if v]
    return {"must": must} if must else None


def _hit(payload, score, origin):
    return {"text": payload.get("text", ""), "source_file": payload.get("source_file", ""),
            "page": str(payload.get("page", "")), "headings": payload.get("headings", ""),
            "domain": payload.get("domain", ""), "project": payload.get("project", ""),
            "score": round(float(score), 4), "origin": origin}


def _embed_query(question):
    try:
        return ollama_embed(question)
    except Exception as e:  # noqa: BLE001
        raise CorpusError(f"Ollama could not embed with {ollama_model()} "
                          f"({os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')}): {e}")


def search(question, k=5, source=None, domain=None, project=None):
    """Top-k chunks for `question`; Qdrant first, the local mirror if Qdrant is down."""
    if not question or not question.strip():
        raise CorpusError("Empty question.")
    k = max(1, min(int(k), 50))
    vec = _embed_query(question)
    store = qdrant()
    server_error = "QDRANT_URL is not set"
    if store is not None:
        try:
            dim = store.dim()
            if len(vec) != dim:
                raise CorpusError(
                    f"{ollama_model()} gives {len(vec)}-dim vectors but {store.collection} is "
                    f"{dim}-dim. Set OLLAMA_EMBED_MODEL to the model that built the collection.")
            rows = store.search(vec, k, _filter(source, domain, project))
            return [_hit(r, r["score"], "server") for r in rows]
        except CorpusError:
            raise
        except (urllib.error.URLError, OSError, KeyError, ValueError) as e:
            server_error = f"{store.url} unreachable: {e}"
    return _search_mirror(vec, k, source, domain, project, server_error)


def _search_mirror(vec, k, source, domain, project, server_error):
    table = _open_mirror()
    if table is None:
        raise CorpusError(f"Server corpus unavailable ({server_error}) and there is no local "
                          f"mirror at {mirror_dir()}. Run scripts/rag/sync.py while online.")
    dim = table.schema.field("vector").type.list_size
    if len(vec) != dim:
        raise CorpusError(f"Mirror is {dim}-dim, {ollama_model()} gives {len(vec)}-dim.")
    query = table.search(vec).metric("cosine").limit(k)
    where = [f"{col} = '{val.replace(chr(39), chr(39) * 2)}'"
             for col, val in (("source_file", source), ("domain", domain), ("project", project))
             if val]
    if where:
        query = query.where(" AND ".join(where), prefilter=True)
    return [_hit(r, 1 - r["_distance"], "mirror") for r in query.to_list()]


def has_table(db, name):
    """`name in db` without the deprecated `table_names()` (the mirror holds one table)."""
    try:
        return name in db.list_tables().tables
    except AttributeError:  # older lancedb
        return name in db.table_names()


def _open_mirror():
    path = mirror_dir()
    if not path.exists():
        return None
    try:
        import lancedb
    except ImportError:
        return None
    db = lancedb.connect(str(path))
    return db.open_table(MIRROR_TABLE) if has_table(db, MIRROR_TABLE) else None


def mirror_meta():
    meta = mirror_dir() / "mirror.json"
    if not meta.exists():
        return None
    return json.loads(meta.read_text(encoding="utf-8"))


def status():
    """What is reachable and whether the embedding model matches the corpus."""
    out = {"collection": collection(), "embed_model": ollama_model(),
           "ollama_host": os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")}
    store = qdrant()
    if store is None:
        out["server"] = {"ok": False, "error": "QDRANT_URL is not set"}
    else:
        try:
            info = store.ping()
            out["server"] = {"ok": True, "url": store.url, "points": info.get("points_count"),
                             "dim": info["config"]["params"]["vectors"]["size"],
                             "status": info.get("status")}
        except Exception as e:  # noqa: BLE001
            out["server"] = {"ok": False, "url": store.url, "error": str(e)}
    try:
        dim = len(ollama_embed("dimension probe"))
        out["embedder"] = {"ok": True, "dim": dim}
        server_dim = out["server"].get("dim")
        if server_dim and server_dim != dim:
            out["embedder"].update(ok=False, error=f"model gives {dim}-dim, corpus is {server_dim}-dim")
    except Exception as e:  # noqa: BLE001
        out["embedder"] = {"ok": False, "error": str(e)}
    meta = mirror_meta()
    out["mirror"] = ({"ok": True, "path": str(mirror_dir()), **meta} if meta
                     else {"ok": False, "path": str(mirror_dir()), "error": "never synced"})
    return out


# --- Ingest -----------------------------------------------------------------

def allowed_roots(default=None):
    """Folders `ingest` may read: `RAG_INGEST_ROOTS` (os.pathsep-separated), else `default`."""
    raw = os.environ.get("RAG_INGEST_ROOTS")
    roots = [p for p in raw.split(os.pathsep) if p.strip()] if raw else ([default] if default else [])
    return [Path(r).expanduser().resolve() for r in roots]


def check_ingest_path(path, roots):
    """Resolve `path` and refuse anything outside `roots` (symlinks and `..` included)."""
    if not roots:
        raise CorpusError("Ingest is disabled: set RAG_INGEST_ROOTS to the folders it may read.")
    target = Path(path).expanduser().resolve()
    if not any(target == r or r in target.parents for r in roots):
        raise CorpusError(f"{target} is outside the allowed ingest folders: "
                          + ", ".join(str(r) for r in roots))
    if not target.is_dir():
        raise CorpusError(f"{target} is not a folder.")
    return target


def point_id(chunk):
    """Stable id, the same scheme as `QdrantStore.upsert_chunks`: re-ingest overwrites."""
    key = f"{chunk['source_file']}|{chunk.get('page', '')}|{chunk['text'][:200]}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def ingest(folder, roots, domain="general", project="", ocr=False, parse=None, batch=32):
    """Parse the PDFs in `folder` with Docling, embed here, upsert into Qdrant.

    Never writes to stdout (stdout is the MCP channel). `parse` is injectable for tests.
    """
    target = check_ingest_path(folder, roots)
    store = qdrant()
    if store is None:
        raise CorpusError("QDRANT_URL is not set; ingest writes to the server corpus only.")
    started = time.time()
    with contextlib.redirect_stdout(sys.stderr):
        if parse is None:
            from ingest import parse_with_docling as parse  # heavy: Docling + torch
        try:
            chunks = parse(target, enable_ocr=ocr)
        except SystemExit as e:
            raise CorpusError(f"Parsing {target} failed: {e}")
    chunks = [c for c in chunks if c.get("text", "").strip()]
    if not chunks:
        raise CorpusError(f"No text extracted from the PDFs in {target}.")
    dim = store.dim()
    model_id = f"ollama:{ollama_model()}"
    written = 0
    for i in range(0, len(chunks), batch):
        part = chunks[i:i + batch]
        vecs = ollama_embed([c["text"] for c in part])
        if len(vecs[0]) != dim:
            raise CorpusError(f"{ollama_model()} gives {len(vecs[0])}-dim vectors, "
                              f"{store.collection} is {dim}-dim.")
        points = [{"id": point_id(c), "vector": v, "payload": {
            "text": c["text"], "source_file": c["source_file"], "page": str(c.get("page", "")),
            "headings": c.get("headings", ""), "domain": c.get("domain", domain),
            "intelligence": c.get("domain", domain), "scope": "local", "project": project,
            "model_id": model_id}} for c, v in zip(part, vecs)]
        _http("PUT", f"{store.url}/collections/{store.collection}/points?wait=true",
              {"points": points}, timeout=store.timeout)
        written += len(points)
    return {"folder": str(target), "files": sorted({c["source_file"] for c in chunks}),
            "chunks": written, "collection": store.collection,
            "seconds": round(time.time() - started, 1)}
