"""
LiteRealm RAG — Document ingestion pipeline (Docling + LanceDB).
Parses PDFs from data/sources/ into a LanceDB vector store in .ai/rag/db.

Usage:
    python .ai/rag/ingest.py
"""

import os
import sys
from pathlib import Path

def ingest():
    root = Path.cwd()
    sources_dir = root / "data" / "sources"
    store_dir = root / ".ai" / "rag" / "db"

    if not sources_dir.exists():
        print(f"No sources directory found at {sources_dir}")
        print("Create it and add PDF files, then run again.")
        sys.exit(1)

    pdf_files = list(sources_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {sources_dir}")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF(s) in {sources_dir}")

    try:
        from docling.document_converter import DocumentConverter
        from docling.chunking import HierarchicalChunker
        import lancedb
        from lancedb.pydantic import LanceModel, Vector
        from lancedb.embeddings import get_registry
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Run bootstrap to install docling and lancedb.")
        sys.exit(1)

    # Initialize LanceDB Embeddings
    try:
        from dotenv import load_dotenv
        load_dotenv(root / ".env")
        api_key = os.environ.get("GEMINI_API_KEY")
        
        if api_key:
            func = get_registry().get("gemini").create(name="models/embedding-001")
            print("Using Gemini cloud embeddings.")
        else:
            func = get_registry().get("sentence-transformers").create(name="all-MiniLM-L6-v2")
            print("Using local sentence-transformers embeddings.")
    except Exception as e:
        print(f"Failed to load embedding model: {e}")
        sys.exit(1)

    # Define LanceDB schema
    class DocumentChunk(LanceModel):
        text: str = func.SourceField()
        vector: Vector(func.ndims()) = func.VectorField()
        source_file: str
        page: str

    print(f"Connecting to LanceDB at {store_dir}...")
    store_dir.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(store_dir))
    table = db.create_table("documents", schema=DocumentChunk, mode="overwrite")

    # Process PDFs
    converter = DocumentConverter()
    chunker = HierarchicalChunker()
    
    total_chunks = 0
    
    for pdf_path in pdf_files:
        print(f"  Parsing: {pdf_path.name}")
        try:
            result = converter.convert(str(pdf_path))
            doc = result.document
            
            chunks = list(chunker.chunk(doc))
            
            data = []
            for chunk in chunks:
                page_num = "?"
                if getattr(chunk.meta, "doc_items", None):
                    for item in chunk.meta.doc_items:
                        if getattr(item, "prov", None):
                            page_num = str(item.prov[0].page_no)
                            break
                            
                data.append({
                    "text": chunk.text,
                    "source_file": pdf_path.name,
                    "page": page_num
                })
                
            if data:
                table.add(data)
                total_chunks += len(data)
                
        except Exception as e:
            print(f"  Error parsing {pdf_path.name}: {e}")

    if total_chunks == 0:
        print("No documents were successfully parsed.")
        sys.exit(1)

    print(f"Done. {total_chunks} chunks indexed in LanceDB.")

if __name__ == "__main__":
    ingest()
