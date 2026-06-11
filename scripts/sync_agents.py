#!/usr/bin/env python3
"""Sync AgentBrain agent definitions into a project's Claude Code subagents.

Source of truth stays in ~/.agentbrain/agents/*.md (tool-agnostic format with
role/triggers/writes_to/never_touches frontmatter). This script converts each
definition into Claude Code's native subagent format and writes it to
<project>/.claude/agents/<name>.md, so the orchestrating Claude session can
delegate via the Task tool instead of doing specialist work in its own context.

Usage:
    python ~/.agentbrain/scripts/sync_agents.py --project-root .
    python ~/.agentbrain/scripts/sync_agents.py --project-root . --check  # CI: no writes

Dependency-free (no PyYAML) — parses the same simple frontmatter that
tests/lint-agents.py lints.
"""
import argparse
import re
import sys
from pathlib import Path

BRAIN = Path(__file__).resolve().parent.parent

# Optional per-agent tool restriction. Omitted -> subagent inherits all tools.
# qa_reviewer is review-only by contract: it may read anything but write only
# docs/REVIEW.md (the Write tool stays enabled; the path limit is in its prompt).
TOOLS = {
    "qa_reviewer": "Read, Grep, Glob, Bash, Write",
}


def parse_agent(text: str):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return None
    fm_text, body = m.group(1), m.group(2)
    fm = {}
    current_key = None
    for line in fm_text.splitlines():
        kv = re.match(r"^([a-z_]+):\s*(.*)$", line)
        item = re.match(r"^\s+-\s+(.*)$", line)
        if kv:
            current_key = kv.group(1)
            val = kv.group(2).strip().strip('"')
            fm[current_key] = [] if val == "" else val
        elif item and current_key and isinstance(fm.get(current_key), list):
            fm[current_key].append(item.group(1).split("#")[0].strip().strip('"'))
    return fm, body.strip()


def build_subagent(src: Path) -> tuple[str, str] | None:
    parsed = parse_agent(src.read_text(encoding="utf-8"))
    if not parsed:
        print(f"SKIP {src.name}: no frontmatter")
        return None
    fm, body = parsed
    name = fm.get("name", src.stem)
    role = fm.get("role", "")
    triggers = fm.get("triggers") or []
    writes_to = fm.get("writes_to") or []
    never = fm.get("never_touches") or []

    trig = "; ".join(f'"{t}"' for t in triggers)
    description = (
        f"{role}. Use PROACTIVELY when the task matches: {trig}. "
        "Delegate matching work here instead of doing it in the main context."
    )

    lines = ["---", f"name: {name}", f"description: {description}"]
    if name in TOOLS:
        lines.append(f"tools: {TOOLS[name]}")
    lines.append("---")
    lines.append("")
    lines.append(
        f"<!-- AUTO-GENERATED from ~/.agentbrain/agents/{src.name} by "
        "sync_agents.py. Edit there, then re-run the sync. -->"
    )
    lines.append("")
    lines.append(body)
    lines.append("")
    lines.append("## Hard path limits (from AgentBrain contract)")
    lines.append("")
    if writes_to:
        lines.append("Write ONLY inside:")
        lines += [f"- `{p}`" for p in writes_to]
        lines.append("")
    if never:
        lines.append("NEVER touch (read is fine unless stated otherwise):")
        lines += [f"- `{p}`" for p in never]
        lines.append("")
    return name, "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", required=True, type=Path)
    ap.add_argument("--check", action="store_true",
                    help="verify outputs are up to date; write nothing")
    args = ap.parse_args()

    out_dir = args.project_root / ".claude" / "agents"
    sources = sorted((BRAIN / "agents").glob("*.md"))
    if not sources:
        print("FAIL: no agent definitions in ~/.agentbrain/agents/")
        return 1

    stale = []
    for src in sources:
        built = build_subagent(src)
        if not built:
            continue
        name, content = built
        dest = out_dir / f"{name}.md"
        if args.check:
            if not dest.exists() or dest.read_text(encoding="utf-8") != content:
                stale.append(dest)
                print(f"STALE {dest}")
            else:
                print(f"OK    {dest.name}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8", newline="\n")
            print(f"WROTE {dest}")

    if args.check and stale:
        print(f"SYNC CHECK FAILED: {len(stale)} stale file(s) — re-run sync_agents.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
