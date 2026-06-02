"""
LiteRealm RAG — Query pipeline with source citations.
Searches the vector store and returns answers with references.

Usage:
    python .ai/rag/query.py "Što je autonomni viličar?"
"""

import os
import sys
import argparse
from pathlib import Path


def load_vectorstore(root, is_global=False):
    """Load existing ChromaDB vector store."""
    if is_global:
        store_dir = Path.home() / ".agentbrain" / "rag" / "db"
    else:
        store_dir = root / ".ai" / "rag" / "db"

    if not store_dir.exists():
        return None

    from dotenv import load_dotenv
    load_dotenv(root / ".env")

    # Match the embedding provider used during ingestion
    embeddings = None
    api_key = os.environ.get("GEMINI_API_KEY")

    if api_key:
        try:
            from langchain_community.embeddings import GoogleGenerativeAIEmbeddings
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=api_key
            )
        except Exception:
            pass

    if embeddings is None:
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        except ImportError:
            print("No embedding provider. Set GEMINI_API_KEY or install sentence-transformers.")
            sys.exit(1)

    from langchain_community.vectorstores import Chroma
    return Chroma(
        persist_directory=str(store_dir),
        embedding_function=embeddings
    )


def query(question: str, k: int = 5, scope: str = "both") -> list[dict]:
    """
    Query the RAG vector store. Returns list of relevant chunks with metadata.
    """
    root = Path.cwd()
    output = []
    
    stores_to_search = []
    if scope in ["local", "both"]:
        local_store = load_vectorstore(root, is_global=False)
        if local_store: stores_to_search.append(("LOCAL", local_store))
        
    if scope in ["global", "both"]:
        global_store = load_vectorstore(root, is_global=True)
        if global_store: stores_to_search.append(("GLOBAL", global_store))

    if not stores_to_search:
        print("No vector stores found. Please run ingest.py first.")
        sys.exit(1)

    for store_name, vectorstore in stores_to_search:
        results = vectorstore.similarity_search(question, k=k)
        for doc in results:
            output.append({
                "content": doc.page_content,
                "source_file": doc.metadata.get("source_file", "unknown"),
                "page": doc.metadata.get("page", "?"),
                "db_scope": store_name
            })

    return output


def main():
    parser = argparse.ArgumentParser(description="Query RAG databases.")
    parser.add_argument("question", nargs="+", help="Question to ask the database")
    parser.add_argument("--scope", choices=["local", "global", "both"], default="both", help="Which database to query")
    args = parser.parse_args()

    question = " ".join(args.question)
    print(f"\nQuery: {question} (Scope: {args.scope})\n")
    print("=" * 60)

    results = query(question, scope=args.scope)

    if not results:
        print("No relevant results found.")
        return

    for i, r in enumerate(results, 1):
        print(f"\n--- Result {i} [{r['db_scope']}] ---")
        print(f"Source: {r['source_file']}, Page: {r['page']}")
        print(f"Content: {r['content'][:500]}...")

    # Print citation summary
    print("\n" + "=" * 60)
    print("Izvori:")
    sources = set()
    for r in results:
        sources.add(f"  [{r['db_scope']}] [{r['source_file']}, str. {r['page']}]")
    for s in sorted(sources):
        print(s)


if __name__ == "__main__":
    main()
