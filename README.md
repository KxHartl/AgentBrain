# AgentBrain

The global toolkit for **LiteRealm** projects — templates, agent definitions, RAG scripts, and skills. Shared across all LiteRealm projects on this machine.

Installed at `~/.agentbrain` by the LiteRealm bootstrap script.

---

## Directory Structure

```
~/.agentbrain/
├── agents/          ← specialized agent definitions (role, triggers, permissions)
├── templates/       ← LaTeX project templates per document type
├── scripts/
│   ├── rag/
│   │   ├── ingest.py       ← index PDFs into LanceDB
│   │   └── query.py        ← search the vector store
│   ├── add_citation.py     ← fetch BibTeX from DOI
│   ├── setup_env.ps1       ← install Python dependencies (Windows)
│   └── setup_env.sh        ← install Python dependencies (Linux/macOS)
├── skills/          ← reusable AI workflows (diagnose, TDD, git workflow...)
├── gotchas/         ← documented failure modes and warnings for agents
├── prompts/         ← reasoning templates (CoT, ReAct, ToT)
├── rag/
│   ├── db/          ← global LanceDB vector store (AgentBrain sources)
│   └── sources/     ← global PDF sources (cross-project reference material)
├── manifest.yaml    ← version contract with LiteRealm projects
└── _TEMPLATE.md     ← format template for new skills/gotchas
```

---

## Setup

The Python environment is set up automatically by LiteRealm's `bootstrap.ps1` / `bootstrap.sh` when `-Rag local` or `global` is requested. To set it up manually:

**Windows:**
```powershell
~/.agentbrain/scripts/setup_env.ps1
```

**Linux / macOS:**
```bash
~/.agentbrain/scripts/setup_env.sh
```

Installs: `docling`, `lancedb`, `sentence-transformers`, `google-generativeai`, `python-dotenv`, `pypdf`

Prefers `uv` for speed; falls back to `pip`.

---

## Agents

Six specialized agents are defined in `agents/`. Each has a YAML header declaring its **role**, **triggers** (phrases that activate it), **writes_to** (directories it may write to), and **never_touches** (hard access restrictions).

| Agent | Role | Key restriction |
|---|---|---|
| `latex_architect` | Set up `docs/` LaTeX structure | Never overwrites existing `main.tex` |
| `data_fetcher` | Find and download literature | Never writes to `docs/` or `src/` |
| `writer` | Write academic LaTeX content | Never overwrites entire `.tex` files |
| `qa_reviewer` | Review and critique content | **Read-only** — only writes `docs/REVIEW.md` |
| `latex_surgeon` | Fix LaTeX compilation errors | Never rewrites content, only compilation fixes |
| `rag_indexer` | Maintain RAG vector database | Never touches `data/sources/` (read-only for it) |

**Pipeline order**: `latex_architect` → `data_fetcher` → `writer` → `qa_reviewer` → `latex_surgeon` → `rag_indexer`

---

## Templates

Available in `templates/`:

| Template | Directory | Format |
|---|---|---|
| FSB Seminar | `fsb-seminar/` | 12pt, A4, Times New Roman |
| FSB Thesis | `fsb-thesis/` | 12pt, A4, with TOC/lists |
| FSB Paper | `fsb-paper/` | 10pt, two-column |
| FSB Presentation | `fsb-presentation/` | Beamer slides |
| FSB Video | `fsb-video/` | Script/storyboard format |

Each template contains:
- `latex/` — `.tex` source files
- `demo.pdf` — compiled example
- `instructions.md` — AI agent instructions for this format
- `structure.md` — document skeleton

See `templates/README.md` for full details.

---

## RAG Scripts

```bash
# Index PDFs from data/sources/ into the local project database
python ~/.agentbrain/scripts/rag/ingest.py

# Index with OCR (for scanned PDFs)
python ~/.agentbrain/scripts/rag/ingest.py --ocr

# Index into the global AgentBrain database
python ~/.agentbrain/scripts/rag/ingest.py --scope global

# Query the vector store
python ~/.agentbrain/scripts/rag/query.py "Your question" --scope both

# Auto-generate BibTeX from DOI
python ~/.agentbrain/scripts/add_citation.py --doi "10.1109/TRO.2024.1234567"
```

**Embeddings**: uses Gemini cloud (`GEMINI_API_KEY` in `.env`) if available, otherwise falls back to local `sentence-transformers` (`all-MiniLM-L6-v2`).

---

## Version Contract

`manifest.yaml` declares the AgentBrain version. LiteRealm's bootstrap stamps the version into the project's `project.yaml` (`agentbrain_version` field). This creates a traceable link between each project and the AgentBrain version it was initialized with.

Current version: **2.0.0** — requires LiteRealm ≥ 2.0.0.

---

## Adding New Knowledge

All knowledge files (`skills/`, `gotchas/`, `prompts/`) must follow the format in `_TEMPLATE.md`:

```markdown
---
domain: [python | rag | latex | workflow | ...]
type: [skill | gotcha | prompt]
author: [your-id or AI]
---
# Title
## Context
## Solution
## Gotchas / Warnings
```
