# AgentBrain

> The shared **brain** behind every [LiteRealm](https://github.com/KxHartl/LiteRealm) project —
> LaTeX templates, AI agent definitions, RAG scripts and hard-won gotchas, installed once per machine.

[![LiteRealm template](https://img.shields.io/badge/works%20with-LiteRealm-6f42c1)](https://github.com/KxHartl/LiteRealm)
[![RAG · Docling + LanceDB](https://img.shields.io/badge/RAG-Docling%20%2B%20LanceDB-008080)](https://docling-project.github.io/docling/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)

AgentBrain lives at `~/.agentbrain`. You never clone it by hand — the first LiteRealm project
you bootstrap clones it for you. One brain serves all your projects; each project stays tiny.

```
   ┌─────────────────────────┐         ┌──────────────────────────────┐
   │  LiteRealm  (a project)  │         │  AgentBrain  (this — shared)  │
   │  · your text, data, PDFs │ ◀────▶  │  · templates · agents         │
   │  · config + state        │  uses   │  · RAG scripts · gotchas      │
   └─────────────────────────┘         └──────────────────────────────┘
```

---

## 📂 Layout

```
~/.agentbrain/
├── agents/          ← agent definitions (role · triggers · writes_to · never_touches)
├── templates/       ← LaTeX templates, one folder per document type
├── scripts/
│   ├── rag/ingest.py   ← full index of data/sources/*.pdf
│   ├── rag/sync.py     ← incremental index of data/sources/** (hash per file)
│   ├── rag/query.py    ← search the vector store
│   ├── rag/classify_source.py ← sort a PDF into standards/regulations/papers/...
│   ├── rag/store_adapter.py   ← Qdrant (QDRANT_URL) first, LanceDB fallback; Ollama embeddings
│   ├── data/experiment_manager.py ← traceable raw → processed runs + EXPERIMENTS_LOG
│   ├── style/          ← check_style (Human Style Score), local_humanizer, learn_style
│   ├── thesis_dashboard.py ← status / audit of a whole thesis
│   ├── add_citation.py ← fetch BibTeX from a DOI
│   ├── sync_agents.py  ← agents/ → project .claude/agents/
│   └── setup_env.{ps1,sh} ← (re)install the RAG Python env
├── style/           ← author_profile.yaml + samples/ (your own writing voice)
├── skills/          ← reusable AI workflows
├── gotchas/         ← documented failure modes for agents
├── prompts/         ← reasoning templates (CoT, ReAct, ToT)
├── rag/{db,sources} ← global vector store + cross-project reference PDFs
├── .venv/           ← the one Python env that powers RAG everywhere
├── manifest.yaml    ← version contract with LiteRealm
└── _TEMPLATE.md     ← format for new skills / gotchas
```

---

## 🤖 Agents

Eight specialists in `agents/`. Each declares its **role**, **triggers** (phrases that activate it),
**writes_to** (allowed directories) and **never_touches** (hard limits).

| Agent | Role | Key restriction |
|---|---|---|
| `latex_architect` | Set up the `docs/` LaTeX project | Never overwrites an existing `main.tex` |
| `data_fetcher` | Find & download literature | Never writes to `docs/` or `src/` |
| `writer` | Write academic LaTeX content | Never overwrites whole `.tex` files |
| `qa_reviewer` | Review & critique | **Read-only** — only writes `docs/REVIEW.md` |
| `latex_surgeon` | Fix compile errors | Touches compilation only, never content |
| `rag_indexer` | Maintain the vector database | `data/sources/` is read-only for it |
| `data_engineer` | Experiments, processing, figures & tables | `data/raw/` append-only; provenance for every result |
| `defense_simulator` | Thesis defense drill | Only writes `docs/DEFENSE_PREP.md` |

**Pipeline:** `latex_architect → data_fetcher → writer → qa_reviewer → latex_surgeon → rag_indexer`

### Claude Code subagents

The definitions here are tool-agnostic. For Claude Code they are additionally synced into a
project as **native subagents** (`.claude/agents/*.md`), so the main session delegates via the
Task tool — each specialist runs in its own context window (cheaper, more focused):

```bash
python ~/.agentbrain/scripts/sync_agents.py --project-root /path/to/project
python ~/.agentbrain/scripts/sync_agents.py --project-root . --check   # CI / staleness check
```

Edit agents **here**, never in `.claude/agents/` (those files are overwritten on sync).

---

## 📐 Templates

| Template | Folder | Format |
|---|---|---|
| FSB Seminar | `fsb-seminar/` | 12 pt, A4, Times |
| FSB Thesis | `fsb-thesis/` | 12 pt, A4, with TOC/lists |
| FSB Paper | `fsb-paper/` | 10 pt, two-column |
| FSB Presentation | `fsb-presentation/` | Beamer slides |
| FSB Video | `fsb-video/` | Script / storyboard |

Each holds `latex/` (source), `demo.pdf` (compiled example), `instructions.md` (agent guidance)
and `structure.md` (document skeleton). See `templates/README.md`.

---

## 📚 RAG — always on

RAG isn't optional and isn't per-project: the scripts and their Python deps live **once** here in
`~/.agentbrain/.venv`, and every LiteRealm project uses them directly.

```bash
# Index a project's PDFs (from its data/sources/) into the project's vector store
python ~/.agentbrain/scripts/rag/ingest.py            # add --ocr for scanned PDFs
python ~/.agentbrain/scripts/rag/ingest.py --scope global   # index into the global store

# Incremental: only new/changed PDFs anywhere under data/sources/
python ~/.agentbrain/scripts/rag/sync.py              # --dry-run, --full, --prune (Qdrant)

# Query
python ~/.agentbrain/scripts/rag/query.py "your question" --scope both

# BibTeX from a DOI
python ~/.agentbrain/scripts/add_citation.py --doi "10.1109/TRO.2024.1234567"
```

**Embeddings**: local Ollama (`OLLAMA_EMBED_MODEL`, e.g. `qwen3-embedding:8b`) when set, then
Gemini (`GEMINI_API_KEY`), otherwise local `sentence-transformers` (`all-MiniLM-L6-v2`);
`RAG_STRICT_EMBED=1` refuses to fall back silently. **Store**: Qdrant when `QDRANT_URL` answers
(the homelab collection is shared — `sync --prune` only deletes points tagged with this project),
otherwise LanceDB in the project's `.ai/rag/db/`.

In projects, call all of this through the LiteRealm helpers (`rag`, `experiment`, `style`,
`thesis` in `.ai/scripts/helpers/`), which pick this venv and pass `--project-root`.

### Setting up the env

You normally don't — it's automatic. LiteRealm bootstrap builds `~/.agentbrain/.venv` on
first run (skipped inside Codespaces to keep container creation light), and the RAG scripts
build it on first `ingest`/`query` if it's still missing. To (re)build it by hand:

```powershell
~/.agentbrain/scripts/setup_env.ps1     # Windows
```
```bash
~/.agentbrain/scripts/setup_env.sh      # Linux / macOS
```

Installs `docling`, `lancedb`, `sentence-transformers`, `google-generativeai`, `python-dotenv`,
`pypdf`. Prefers `uv`; falls back to `pip`.

---

## 🔗 Version contract

`manifest.yaml` declares the AgentBrain version (currently **2.1.0**, requires LiteRealm ≥ 2.0.0).
Bootstrap stamps that version + commit into each project's `project.yaml`
(`agentbrain_version`), so every project records exactly which brain built it.

---

## ➕ Adding knowledge

New `skills/`, `gotchas/` and `prompts/` follow `_TEMPLATE.md`:

```markdown
---
domain: [python | rag | latex | workflow | ...]
type:   [skill | gotcha | prompt]
author: [your-id or AI]
---
# Title
## Context
## Solution
## Gotchas / Warnings
```

Agents are encouraged to update this brain themselves when they discover a new gotcha or workflow.
