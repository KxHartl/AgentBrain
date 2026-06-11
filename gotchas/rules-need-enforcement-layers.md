---
domain: workflow
type: gotcha
author: AI
verified: "2026-06, LiteRealm/AgentBrain orchestration overhaul"
---
# Prose rules alone don't bind agents — use enforcement layers

## Context

Rules written only in CLAUDE.md / GEMINI.md (e.g. "commit after every logical
unit", "never touch data/raw/") are *probabilistic*: every model weighs them
differently, and compliance degrades as context fills up. Observed in practice:
Gemini CLI and Antigravity routinely skipped the proactive-git rule that Claude
mostly followed.

## Solution

Layer the rules by how strongly each layer binds, and push every rule as far
down as it can go:

1. **VCS-level (binds everything, even humans)** — git hooks.
   E.g. LiteRealm's pre-commit hook rejects commits touching `data/raw/`.
2. **Harness-level (binds one tool deterministically)** — Claude Code hooks in
   `.claude/settings.json`: PreToolUse deny for `data/raw/` writes, Stop hook
   that blocks finishing with a dirty working tree.
3. **Ergonomics (makes the right thing the easy thing)** — one-shot helpers.
   A `checkpoint.ps1|sh "feat: msg"` that does add+commit+AI-prefix is followed
   far more reliably than a 3-step prose instruction.
4. **Prose (single source of truth, last resort)** — one canonical `AGENTS.md`
   imported by thin CLAUDE.md/GEMINI.md shims. Never duplicate rule text per
   tool: duplicated rules drift, and drifted rules get ignored.

## Gotchas / Warnings

- A Stop-hook that force-blocks must honor `stop_hook_active` or it loops forever.
- Tools without a hook system (Gemini CLI, Antigravity) only get layers 1, 3, 4 —
  their context file must say explicitly that *they* are the safety net.
- Don't name the on-demand reference file `AGENTS.md` inside subfolders: several
  harnesses auto-load any `AGENTS.md` they find, silently burning tokens.
