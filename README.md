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
│   ├── rag/ingest.py   ← index PDFs into LanceDB
│   ├── rag/query.py    ← search the vector store
│   ├── add_citation.py ← fetch BibTeX from a DOI
│   └── setup_env.{ps1,sh} ← (re)install the RAG Python env
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

Six specialists in `agents/`. Each declares its **role**, **triggers** (phrases that activate it),
**writes_to** (allowed directories) and **never_touches** (hard limits).

| Agent | Role | Key restriction |
|---|---|---|
| `latex_architect` | Set up the `docs/` LaTeX project | Never overwrites an existing `main.tex` |
| `data_fetcher` | Find & download literature | Never writes to `docs/` or `src/` |
| `writer` | Write academic LaTeX content | Never overwrites whole `.tex` files |
| `qa_reviewer` | Review & critique | **Read-only** — only writes `docs/REVIEW.md` |
| `latex_surgeon` | Fix compile errors | Touches compilation only, never content |
| `rag_indexer` | Maintain the vector database | `data/sources/` is read-only for it |

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

# Query
python ~/.agentbrain/scripts/rag/query.py "your question" --scope both

# BibTeX from a DOI
python ~/.agentbrain/scripts/add_citation.py --doi "10.1109/TRO.2024.1234567"
```

**Embeddings** use Gemini cloud when `GEMINI_API_KEY` is present in the project's `.env`,
otherwise local `sentence-transformers` (`all-MiniLM-L6-v2`). No configuration switch — it adapts.

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
