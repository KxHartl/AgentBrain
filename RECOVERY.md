# Recovery record — 2026-09-25

The work disk that held `~/.agentbrain` failed. Everything committed after `8983e7c`
(11 Jun 2026, v2.2.0) was local only and is gone; the last project that used it pinned
`agentbrain_commit: 36a77c4`, which never reached GitHub.

## Rebuilt (v2.3.0)

| Item | From |
|---|---|
| `scripts/rag/store_adapter.py` (Qdrant first, LanceDB fallback, Ollama embeddings) | the interface the thesis repo still calls |
| `OLLAMA_EMBED_MODEL`, `RAG_STRICT_EMBED`, `QDRANT_*` in `ingest.py` / `query.py` | the thesis repo `.env.example` |
| `agents/*.md` (8 agents incl. `data_engineer`, `defense_simulator`, staging gate) | the generated `.claude/agents/` mirrors (25 Aug); `sync_agents.py --check` round-trips clean |

The Qdrant corpus itself lives on the homelab and survived (`agentbrain_corpus_8b`, 51,915 points).

## Still missing — referenced but not rebuilt

- `scripts/rag/sync.py`, `scripts/rag/classify_source.py` (called by `rag.ps1 sync|classify`)
- `scripts/thesis_dashboard.py` (called by `thesis.ps1`)
- `style/author_profile.yaml`, `style/samples/` (read by the `writer` agent)
- Whatever was in `gotchas/`, `skills/`, `prompts/` and `templates/` after June

**Rule from now on: push after every commit.** The `post-commit` hook in `scripts/hooks/` does it.
