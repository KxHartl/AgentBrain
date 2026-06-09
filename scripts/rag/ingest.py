"""
LiteRealm RAG — Document ingestion pipeline (Docling + LanceDB).
Uses IBM Docling for ML-based PDF parsing (tables, layout, figures, multi-column)
and stores embeddings in a LanceDB vector store.

Usage:
    python ~/.agentbrain/scripts/rag/ingest.py                    # local project DB
    python ~/.agentbrain/scripts/rag/ingest.py --scope global     # global AgentBrain DB
    python ~/.agentbrain/scripts/rag/ingest.py --ocr              # enable OCR for scanned PDFs
"""

import os
import sys
import argparse
from pathlib import Path


def ensure_brain_venv():
    """Re-exec under the AgentBrain venv if the current interpreter lacks RAG deps.

    Lets `python ~/.agentbrain/scripts/rag/ingest.py` work even when invoked with a
    plain `python` that has no docling/lancedb — the heavy deps live in the brain venv.
    """
    import importlib.util
    if importlib.util.find_spec("lancedb") is not None:
        return
    brain = Path(os.environ.get("AGENTBRAIN_PATH") or (Path.home() / ".agentbrain"))
    for cand in (brain / ".venv" / "bin" / "python", brain / ".venv" / "Scripts" / "python.exe"):
        if cand.exists() and Path(sys.executable).resolve() != cand.resolve():
            # subprocess (not os.execv): execv is async on Windows and would let the
            # caller return before this finishes. run() waits and propagates the code.
            import subprocess
            sys.exit(subprocess.run([str(cand), *sys.argv]).returncode)


def get_paths(scope):
    """Return (sources_dir, store_dir) based on scope."""
    if scope == "global":
        root = Path.home() / ".agentbrain"
        return root / "rag" / "sources", root / "rag" / "db"
    else:
        root = Path.cwd()
        return root / "data" / "sources", root / ".ai" / "rag" / "db"


def load_embeddings():
    """Load embedding model: prefer Gemini cloud, fall back to local."""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            def embed_fn(texts):
                result = genai.embed_content(
                    model="models/embedding-001",
                    content=texts if isinstance(texts, list) else [texts],
                    task_type="retrieval_document"
                )
                return result["embedding"]

            print("Using Gemini cloud embeddings.")
            return embed_fn, 768, "gemini:models/embedding-001"
        except Exception as e:
            print(f"  Gemini failed ({e}), trying local...")

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")

        def embed_fn(texts):
            if isinstance(texts, str):
                texts = [texts]
            return model.encode(texts).tolist()

        print("Using local HuggingFace embeddings (all-MiniLM-L6-v2).")
        return embed_fn, 384, "local:all-MiniLM-L6-v2"
    except ImportError:
        print("No embedding provider available.")
        print("Set GEMINI_API_KEY in .env or: pip install sentence-transformers")
        sys.exit(1)


def parse_with_docling(sources_dir, enable_ocr=False):
    """
    Parse PDFs using Docling DocumentConverter + HybridChunker.
    Handles tables, multi-column layouts, figures, and complex formatting.
    """
    try:
        from docling.document_converter import DocumentConverter
        from docling.chunking import HybridChunker
    except ImportError:
        print("Docling not installed. Run: pip install docling")
        print("Note: Docling requires Python 3.10+ and is ~500MB (includes ML models).")
        sys.exit(1)

    pdf_files = list(sources_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {sources_dir}")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF(s) in {sources_dir}")

    # Configure converter
    if enable_ocr:
        from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import PdfFormatOption

        ocr_options = EasyOcrOptions(force_full_page_ocr=True)
        pipeline_options = PdfPipelineOptions(ocr_options=ocr_options)
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        print("  OCR enabled (full page).")
    else:
        converter = DocumentConverter()

    # Configure chunker
    chunker = HybridChunker(max_tokens=512, merge_peers=True)

    all_chunks = []

    for pdf_path in pdf_files:
        print(f"  Parsing: {pdf_path.name} (Docling ML pipeline)...")
        try:
            result = converter.convert(str(pdf_path))
            doc = result.document

            chunks = list(chunker.chunk(doc))

            for chunk in chunks:
                text = chunker.contextualize(chunk)
                if not text.strip():
                    continue

                meta = chunk.meta
                page_no = 0
                doc_items = getattr(meta, "doc_items", None)
                if doc_items and doc_items[0].prov:
                    page_no = doc_items[0].prov[0].page_no

                headings = getattr(meta, "headings", None)
                headings_str = " > ".join(headings) if headings else ""

                all_chunks.append({
                    "text": text,
                    "source_file": pdf_path.name,
                    "page": page_no,
                    "headings": headings_str,
                })

            print(f"    -> {len(chunks)} chunks extracted")

        except Exception as e:
            print(f"  Error parsing {pdf_path.name}: {e}")
            print(f"    Falling back to basic text extraction...")
            fallback_chunks = _fallback_parse(pdf_path)
            all_chunks.extend(fallback_chunks)

    return all_chunks


def _fallback_parse(pdf_path):
    """Fallback parser using pypdf when Docling fails on a specific file."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        chunks = []
        chunk_size = 1000
        chunk_overlap = 200

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end]
                if chunk_text.strip():
                    chunks.append({
                        "text": chunk_text,
                        "source_file": pdf_path.name,
                        "page": page_num + 1,
                        "headings": "",
                    })
                start += chunk_size - chunk_overlap

        print(f"    -> {len(chunks)} chunks (fallback pypdf)")
        return chunks
    except Exception as e:
        print(f"    Fallback also failed: {e}")
        return []


def parse_fast(sources_dir):
    """Lightweight pypdf-only parsing — skips the ~500MB Docling ML pipeline.

    Used by --fast (and CI smoke tests) where layout-aware parsing is not needed.
    """
    pdf_files = list(sources_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {sources_dir}")
        sys.exit(1)
    print(f"Found {len(pdf_files)} PDF(s) in {sources_dir} (fast pypdf mode)")
    all_chunks = []
    for pdf_path in pdf_files:
        print(f"  Parsing: {pdf_path.name} (pypdf)...")
        all_chunks.extend(_fallback_parse(pdf_path))
    return all_chunks


def ingest(scope="local", enable_ocr=False, fast=False):
    """Main ingestion pipeline."""
    sources_dir, store_dir = get_paths(scope)

    if not sources_dir.exists():
        print(f"No sources directory found at {sources_dir}")
        print("Create it and add PDF files, then run again.")
        sys.exit(1)

    # Parse PDFs (fast pypdf, or layout-aware Docling)
    chunks = parse_fast(sources_dir) if fast else parse_with_docling(sources_dir, enable_ocr=enable_ocr)
    if not chunks:
        print("No text extracted from PDFs.")
        sys.exit(1)

    print(f"\nTotal chunks: {len(chunks)}")

    # Load embeddings
    embed_fn, dim, model_id = load_embeddings()

    # Generate embeddings in batches
    print("Generating embeddings...")
    batch_size = 64
    all_embeddings = []
    texts = [c["text"] for c in chunks]

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = embed_fn(batch)
        all_embeddings.extend(embeddings)
        print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)}")

    # Build records for LanceDB
    records = []
    for chunk, embedding in zip(chunks, all_embeddings):
        records.append({
            "text": chunk["text"],
            "source_file": chunk["source_file"],
            "page": chunk["page"],
            "headings": chunk.get("headings", ""),
            "vector": embedding,
        })

    # Store in LanceDB
    try:
        import lancedb
    except ImportError:
        print("lancedb not installed. Run: pip install lancedb")
        sys.exit(1)

    store_dir.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(store_dir))

    table_name = "global_docs" if scope == "global" else "project_docs"

    # NOTE: table_names() emits a DeprecationWarning in lancedb 0.33 but still works
    # and returns a plain list; list_tables() returns a paginated response object.
    if table_name in db.table_names():
        db.drop_table(table_name)

    table = db.create_table(table_name, data=records)

    # Record which embedding model/dim built this index so query.py can match it
    # (prevents a silent dimension mismatch when the query-time model differs).
    import json
    (store_dir / "embedding_meta.json").write_text(
        json.dumps({"model": model_id, "dim": dim, "table": table_name}, indent=2),
        encoding="utf-8",
    )

    print(f"\nDone. {len(records)} chunks indexed in '{table_name}' at {store_dir}")
    print(f"Embedding model: {model_id} (dim {dim})")

    return table


if __name__ == "__main__":
    ensure_brain_venv()
    parser = argparse.ArgumentParser(description="Ingest PDFs into LanceDB (Docling parser).")
    parser.add_argument("--scope", choices=["local", "global"], default="local",
                        help="Choose local project or global AgentBrain database.")
    parser.add_argument("--ocr", action="store_true",
                        help="Enable full-page OCR for scanned PDFs (slower).")
    parser.add_argument("--fast", action="store_true",
                        help="Skip Docling ML pipeline; use lightweight pypdf parsing (CI/smoke).")
    args = parser.parse_args()
    ingest(scope=args.scope, enable_ocr=args.ocr, fast=args.fast)
