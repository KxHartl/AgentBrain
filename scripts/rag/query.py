"""
LiteRealm RAG — Query pipeline with source citations (LanceDB).
Searches vector stores and returns relevant chunks with references.

Usage:
    python ~/.agentbrain/scripts/rag/query.py "Sto je autonomni vilicar?"
    python ~/.agentbrain/scripts/rag/query.py "question" --scope local
    python ~/.agentbrain/scripts/rag/query.py "question" --scope global
    python ~/.agentbrain/scripts/rag/query.py "question" --scope both
"""

import os
import sys
import argparse
from pathlib import Path


def load_embed_fn():
    """Load the same embedding model used during ingestion."""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            def embed_fn(text):
                result = genai.embed_content(
                    model="models/embedding-001",
                    content=text,
                    task_type="retrieval_query"
                )
                return result["embedding"]

            return embed_fn
        except Exception:
            pass

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")

        def embed_fn(text):
            return model.encode(text).tolist()

        return embed_fn
    except ImportError:
        print("No embedding provider. Set GEMINI_API_KEY or install sentence-transformers.")
        sys.exit(1)


def query(question, k=5, scope="both", local_weight=0.7, global_weight=0.3):
    """
    Query LanceDB vector stores. Returns ranked list of relevant chunks.
    """
    try:
        import lancedb
    except ImportError:
        print("lancedb not installed. Run: pip install lancedb")
        sys.exit(1)

    embed_fn = load_embed_fn()
    query_vec = embed_fn(question)

    root = Path.cwd()
    results = []

    stores = []
    if scope in ("local", "both"):
        local_db_path = root / ".ai" / "rag" / "db"
        if local_db_path.exists():
            stores.append(("LOCAL", str(local_db_path), "project_docs", local_weight))

    if scope in ("global", "both"):
        global_db_path = Path.home() / ".agentbrain" / "rag" / "db"
        if global_db_path.exists():
            stores.append(("GLOBAL", str(global_db_path), "global_docs", global_weight))

    if not stores:
        print("No vector stores found. Run ingest.py first.")
        sys.exit(1)

    for store_name, db_path, table_name, weight in stores:
        try:
            db = lancedb.connect(db_path)
            if table_name not in db.table_names():
                continue

            table = db.open_table(table_name)
            search_results = table.search(query_vec).limit(k).to_list()

            for row in search_results:
                results.append({
                    "text": row["text"],
                    "source_file": row["source_file"],
                    "page": row["page"],
                    "headings": row.get("headings", ""),
                    "distance": row.get("_distance", 0),
                    "weighted_score": (1 / (1 + row.get("_distance", 0))) * weight,
                    "db_scope": store_name,
                })
        except Exception as e:
            print(f"  Warning: Could not query {store_name} store: {e}")

    results.sort(key=lambda r: r["weighted_score"], reverse=True)
    return results


def main():
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
        print(f"Content: {r['text'][:500]}...")

    print("\n" + "=" * 60)
    print("Izvori:")
    sources = set()
    for r in results:
        src = f"  [{r['db_scope']}] [{r['source_file']}, str. {r['page']}]"
        sources.add(src)
    for s in sorted(sources):
        print(s)


if __name__ == "__main__":
    main()
