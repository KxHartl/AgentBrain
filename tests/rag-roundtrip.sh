#!/usr/bin/env bash
# RAG smoke test: ingest a fixture PDF into a throwaway project, then query it.
# Forces local embeddings (--fast pypdf, no Gemini) for a deterministic offline run.
# Verifies the local DB lands in <project>/.ai/rag/db (NOT inside the brain).
set -u

BRAIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python}"

if [[ ! -f "$BRAIN_ROOT/tests/fixtures/bitcoin.pdf" ]]; then
  echo "ERROR: missing tests/fixtures/bitcoin.pdf" >&2
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/data/sources"
cp "$BRAIN_ROOT/tests/fixtures/bitcoin.pdf" "$tmp/data/sources/"

unset GEMINI_API_KEY   # force local (384-dim) embeddings for determinism
cd "$tmp"

echo "--- ingest ---"
if ! "$PY" "$BRAIN_ROOT/scripts/rag/ingest.py" --scope local --fast; then
  echo "INGEST FAILED"; exit 1
fi

if [[ ! -d "$tmp/.ai/rag/db" ]]; then
  echo "FAIL: local DB not created in project .ai/rag/db"; exit 1
fi
if [[ -d "$BRAIN_ROOT/rag/local_dbs" ]]; then
  echo "FAIL: brain rag/local_dbs/ must not exist (per-project data belongs in the project)"; exit 1
fi
if [[ ! -f "$tmp/.ai/rag/db/embedding_meta.json" ]]; then
  echo "FAIL: embedding_meta.json sidecar not written"; exit 1
fi

echo "--- query ---"
out="$("$PY" "$BRAIN_ROOT/scripts/rag/query.py" "bitcoin electronic cash" --scope local -k 3)"
echo "$out"
if ! echo "$out" | grep -qi "bitcoin.pdf"; then
  echo "FAIL: query returned no result from bitcoin.pdf"; exit 1
fi

echo "--- sync (incremental, nested sources) ---"
rm -rf "$tmp/.ai/rag/db"
mkdir -p "$tmp/data/sources/papers"
mv "$tmp/data/sources/bitcoin.pdf" "$tmp/data/sources/papers/"
if ! "$PY" "$BRAIN_ROOT/scripts/rag/sync.py" --fast; then
  echo "FAIL: first sync"; exit 1
fi
out="$("$PY" "$BRAIN_ROOT/scripts/rag/sync.py" --fast --dry-run)"
if ! echo "$out" | grep -q "0 new, 0 changed, 0 removed, 1 unchanged"; then
  echo "$out"; echo "FAIL: second sync is not a no-op"; exit 1
fi
out="$("$PY" "$BRAIN_ROOT/scripts/rag/query.py" "bitcoin electronic cash" --scope local -k 3)"
if ! echo "$out" | grep -qi "bitcoin.pdf"; then
  echo "FAIL: query after sync returned nothing from bitcoin.pdf"; exit 1
fi

echo "RAG ROUNDTRIP TEST: PASSED"
