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

| `agents/kev/*.md` (`adr_consolidator`, `conformance_runner`, `source_fetcher`) — 2026-10-12 | the KEV repo's `.claude/agents/` mirrors; `sync_agents.py --check --namespace kev` round-trips clean |
| `sync_agents.py --namespace` — 2026-10-12 | KEV AGENTS.md §8 calls it; without it a sync would hand KEV the LiteRealm agents |

| `scripts/rag/sync.py` — 2026-10-16 | rebuilt as a Qdrant → local LanceDB mirror (vectors copied, incremental); the original's exact behaviour is unknown |

The Qdrant corpus itself lives on the homelab and survived (`agentbrain_corpus_8b`, 51,915 points).

## Rebuilt (v2.4.0, 29 Sep) — from the interfaces that still call them

No copy of the originals survived, so these are new implementations of the contracts in the
LiteRealm helpers (`rag.*`, `experiment.*`, `style.*`, `thesis.*`) and the agent definitions.
Behaviour may differ in detail from the lost versions; each is covered by `tests/`.

| Item | Contract it satisfies |
|---|---|
| `scripts/rag/sync_sources.py` | `rag sync` (renamed: `sync.py` is now the corpus mirror) — incremental, recursive; Qdrant points tagged by project, `--prune` only deletes those |
| `scripts/rag/classify_source.py` | `rag classify` — category for `data/staging/<category>/` |
| `scripts/thesis_dashboard.py` | `thesis status\|audit --project-root .` |
| `scripts/data/experiment_manager.py` | `experiment new\|process\|list\|audit` and the `data_engineer` agent |
| `scripts/style/{check_style,local_humanizer,learn_style}.py` | `style check\|humanize\|learn`, "Human Style Score > 75" in `qa_reviewer` |
| `style/author_profile.yaml`, `style/samples/` | skeleton only — the learned profile is gone |

## Still missing — needs the author

- The learned **author profile and writing samples**: re-learn from chapters you wrote yourself,
  `style.sh learn docs/chapters/<file>.tex --save-sample`.
- Whatever was in `gotchas/`, `skills/`, `prompts/` and `templates/` after June — nothing references
  it, so there is no contract to rebuild from.

**Rule from now on: push after every commit.** The `post-commit` hook in `scripts/hooks/` does it.
