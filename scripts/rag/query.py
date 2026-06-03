"""
LiteRealm RAG — Query pipeline with source citations (LanceDB).
Searches the LanceDB vector store and returns answers with references.

Usage (run from the LiteRealm project root):
    python ~/.agentbrain/scripts/rag/query.py "Što je autonomni viličar?"
"""

import sys
from pathlib import Path

def query(question: str, k: int = 5) -> list[dict]:
    root = Path.cwd()
    store_dir = root / ".ai" / "rag" / "db"

    if not store_dir.exists():
        print("Vector store not found. Run ingest.py first:")
        print("  python .ai/rag/ingest.py")
        sys.exit(1)

    try:
        import lancedb
        from lancedb.embeddings import get_registry
        from dotenv import load_dotenv
        import os
        
        load_dotenv(root / ".env")
        # We need to register the same embedding function so LanceDB knows how to embed the query
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            func = get_registry().get("gemini").create(name="models/embedding-001")
        else:
            func = get_registry().get("sentence-transformers").create(name="all-MiniLM-L6-v2")
            
    except ImportError:
        print("Missing dependency: lancedb, python-dotenv, or embedding providers")
        sys.exit(1)

    db = lancedb.connect(str(store_dir))
    if "documents" not in db.table_names():
        print("Table 'documents' not found in vector store.")
        sys.exit(1)

    table = db.open_table("documents")
    results = table.search(question).limit(k).to_list()

    output = []
    for r in results:
        output.append({
            "content": r.get("text", ""),
            "source_file": r.get("source_file", "unknown"),
            "page": r.get("page", "?"),
        })

    return output

def main():
    if len(sys.argv) < 2:
        print("Usage: python .ai/rag/query.py \"Your question here\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"\nQuery: {question}\n")
    print("=" * 60)

    results = query(question)

    if not results:
        print("No relevant results found.")
        return

    for i, r in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"Source: {r['source_file']}, Page: {r['page']}")
        print(f"Content: {r['content'][:500]}...")

    print("\n" + "=" * 60)
    print("Izvori:")
    sources = set()
    for r in results:
        sources.add(f"  [{r['source_file']}, str. {r['page']}]")
    for s in sorted(sources):
        print(s)

if __name__ == "__main__":
    main()
