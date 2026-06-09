"""
LiteRealm RAG — Query pipeline with source citations (LanceDB).
Searches vector stores and returns relevant chunks with references.

The query-time embedding model is chosen to MATCH the model that built each
index (detected from the stored vector dimension), so a mismatch fails loudly
with a fix hint instead of silently returning nothing.

Usage:
    python ~/.agentbrain/scripts/rag/query.py "Sto je autonomni vilicar?"
    python ~/.agentbrain/scripts/rag/query.py "question" --scope local
    python ~/.agentbrain/scripts/rag/query.py "question" --scope global
    python ~/.agentbrain/scripts/rag/query.py "question" --scope both
"""

import os
import re
import sys
import argparse
from pathlib import Path

# Resolve store paths through the shared helper (same dir as this script) so
# query reads from the exact location ingest wrote to, incl. FAT/exFAT relocation.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rag_paths import resolve_store_dir, enable_utf8_io


def load_cite_keys(bib_path):
    """Map a source PDF's basename -> its BibTeX \\cite key, via the 'file' field.

    Lets query annotate each retrieved chunk with the exact \\cite key, so the writer
    cites deterministically instead of guessing. Returns {} if references.bib is
    missing or unreadable (key annotation is then simply omitted).
    """
    try:
        text = Path(bib_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    mapping = {}
    # Split into entries: @type{key, ...body...} up to the next entry or EOF.
    for m in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,(.*?)(?=@\w+\s*\{|\Z)", text, re.DOTALL):
        key, body = m.group(1), m.group(2)
        fm = re.search(r"\bfile\s*=\s*[{\"]([^}\"]+)[}\"]", body, re.IGNORECASE)
        if fm:
            # references.bib stores a relative path like 'data/sources/paper.pdf'.
            base = os.path.basename(fm.group(1).strip().replace("\\", "/").rstrip("/"))
            if base:
                mapping[base] = key
    return mapping


def ensure_brain_venv():
    """Run under the AgentBrain venv; build it on first use if it is missing.

    Lets the RAG scripts work even when invoked with a plain `python` that has no
    docling/lancedb — the heavy deps live in the shared brain venv. If that venv
    doesn't exist yet (fresh clone / Codespace), build it once via setup_env and
    re-exec under it. Guarded against re-exec loops.
    """
    import importlib.util
    import subprocess
    if importlib.util.find_spec("lancedb") is not None:
        return  # deps already available in this interpreter

    brain = Path(os.environ.get("AGENTBRAIN_PATH") or (Path.home() / ".agentbrain"))
    venv_pythons = (brain / ".venv" / "bin" / "python", brain / ".venv" / "Scripts" / "python.exe")
    vpy = next((c for c in venv_pythons if c.exists()), None)

    # Brain venv exists and we're not in it → re-exec under it.
    # subprocess (not os.execv): execv is async on Windows and would let the caller
    # return before this finishes. run() waits and propagates the exit code.
    if vpy and Path(sys.executable).resolve() != vpy.resolve():
        sys.exit(subprocess.run([str(vpy), *sys.argv]).returncode)

    # No usable venv. Build it once, then re-exec; the sentinel prevents a loop.
    if os.environ.get("_AGENTBRAIN_VENV_TRIED"):
        return  # already tried — let the caller's import error report the missing dep
    setup = brain / "scripts" / ("setup_env.ps1" if os.name == "nt" else "setup_env.sh")
    if not setup.exists():
        return
    setup_cmd = (["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(setup)]
                 if os.name == "nt" else ["bash", str(setup)])
    print("RAG deps not found — building the AgentBrain environment "
          "(one-time, a few minutes)...", flush=True)
    if subprocess.run(setup_cmd).returncode != 0:
        return  # setup failed; caller will report the missing dependency
    vpy = next((c for c in venv_pythons if c.exists()), None)
    if vpy:
        env = {**os.environ, "_AGENTBRAIN_VENV_TRIED": "1"}
        sys.exit(subprocess.run([str(vpy), *sys.argv], env=env).returncode)


def embedder_for_dim(dim):
    """Return an embed_fn whose output matches the stored vector dim, or raise.

    768 -> Gemini cloud (requires GEMINI_API_KEY); 384 -> local MiniLM.
    """
    from dotenv import load_dotenv
    load_dotenv()

    if dim == 768:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "This index was built with Gemini embeddings (dim 768) but "
                "GEMINI_API_KEY is not set. Set it in .env, or re-ingest with "
                "local embeddings (unset GEMINI_API_KEY before running ingest.py)."
            )
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        def embed_fn(text):
            return genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_query",
            )["embedding"]

        return embed_fn

    if dim == 384:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise RuntimeError(
                "Index uses local embeddings (dim 384) but sentence-transformers "
                "is not installed. Run: pip install sentence-transformers"
            )
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return lambda text: model.encode(text).tolist()

    raise RuntimeError(
        f"Stored vector dimension {dim} has no known embedding model. "
        "Re-ingest the sources with a supported embedder."
    )


def get_vector_dim(table):
    """Read the vector dimension from a LanceDB table schema."""
    try:
        return table.schema.field("vector").type.list_size
    except Exception:
        row = table.search().limit(1).to_list()
        return len(row[0]["vector"]) if row else None


def query(question, k=5, scope="both", local_weight=0.7, global_weight=0.3):
    """Query LanceDB vector stores. Returns a ranked list of relevant chunks."""
    try:
        import lancedb
    except ImportError:
        print("lancedb not installed. Run: pip install lancedb")
        sys.exit(1)

    root = Path.cwd()
    results = []

    # PDF basename -> \cite key, so each result carries the exact citation key.
    cite_keys = load_cite_keys(root / "docs" / "references.bib")

    stores = []
    if scope in ("local", "both"):
        local_db_path = resolve_store_dir(root / ".ai" / "rag" / "db", project_root=root)
        if local_db_path.exists():
            stores.append(("LOCAL", str(local_db_path), "project_docs", local_weight))

    if scope in ("global", "both"):
        brain = Path.home() / ".agentbrain"
        global_db_path = resolve_store_dir(brain / "rag" / "db", project_root=brain)
        if global_db_path.exists():
            stores.append(("GLOBAL", str(global_db_path), "global_docs", global_weight))

    if not stores:
        print("No vector stores found. Run ingest.py first.")
        sys.exit(1)

    embedders = {}  # dim -> embed_fn (cache; a query model loads once)
    for store_name, db_path, table_name, weight in stores:
        try:
            db = lancedb.connect(db_path)
            if table_name not in db.table_names():  # plain list; list_tables() is paginated
                continue
            table = db.open_table(table_name)
            dim = get_vector_dim(table)
            if dim not in embedders:
                embedders[dim] = embedder_for_dim(dim)
            query_vec = embedders[dim](question)
            search_results = table.search(query_vec).limit(k).to_list()

            for row in search_results:
                results.append({
                    "text": row["text"],
                    "source_file": row["source_file"],
                    "page": row["page"],
                    "headings": row.get("headings", ""),
                    "cite_key": cite_keys.get(row["source_file"], ""),
                    "distance": row.get("_distance", 0),
                    "weighted_score": (1 / (1 + row.get("_distance", 0))) * weight,
                    "db_scope": store_name,
                })
        except RuntimeError:
            # Embedding-model mismatch is a hard error — surface it, do not hide it.
            raise
        except Exception as e:
            print(f"  Warning: Could not query {store_name} store: {e}")

    results.sort(key=lambda r: r["weighted_score"], reverse=True)
    return results


def main():
    enable_utf8_io()
    ensure_brain_venv()
    parser = argparse.ArgumentParser(description="Query LanceDB RAG databases.")
    parser.add_argument("question", nargs="+", help="Question to ask the database")
    parser.add_argument("--scope", choices=["local", "global", "both"], default="both",
                        help="Which database to query")
    parser.add_argument("-k", type=int, default=5, help="Number of results per store")
    args = parser.parse_args()

    question = " ".join(args.question)
    print(f"\nQuery: {question} (Scope: {args.scope})\n")
    print("=" * 60)

    results = query(question, k=args.k, scope=args.scope)

    if not results:
        print("No relevant results found.")
        return

    for i, r in enumerate(results, 1):
        score_pct = r["weighted_score"] * 100
        print(f"\n--- Result {i} [{r['db_scope']}] (relevance: {score_pct:.0f}%) ---")
        print(f"Source: {r['source_file']}, Page: {r['page']}")
        if r.get("headings"):
            print(f"Section: {r['headings']}")
        if r.get("cite_key"):
            print(f"Citiraj: \\cite[str.~{r['page']}]{{{r['cite_key']}}}")
        print(f"Content: {r['text'][:500]}...")

    print("\n" + "=" * 60)
    print("Izvori:")
    sources = set()
    for r in results:
        cite = f" -> \\cite{{{r['cite_key']}}}" if r.get("cite_key") else ""
        src = f"  [{r['db_scope']}] [{r['source_file']}, str. {r['page']}]{cite}"
        sources.add(src)
    for s in sorted(sources):
        print(s)
    if any(not r.get("cite_key") for r in results):
        print("\n  (Bez \\cite ključa = nema unosa u docs/references.bib s 'file' poljem "
              "za taj PDF. data_fetcher treba dodati citat s --file.)")


if __name__ == "__main__":
    main()
