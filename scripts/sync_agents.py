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
    python ~/.agentbrain/scripts/sync_agents.py --project-root . --namespace kev
    python ~/.agentbrain/scripts/sync_agents.py --project-root . --namespace work --tier task --prune

--namespace NAME reads ~/.agentbrain/agents/NAME/*.md instead of agents/*.md, so a
project whose agents are not LiteRealm's (KEV) never receives the academic ones.
Several namespaces may be given comma-separated (work,shared).

--tier T keeps only agents whose optional `tiers:` list contains T (WorkRealm tiers:
quick, task, project). Agents without `tiers:` are always kept.

--prune deletes generated agents (files carrying this script's AUTO-GENERATED marker)
whose source no longer exists or no longer matches the selection. Hand-written agents
in .claude/agents/ are never touched. With --check, would-be-pruned files count as stale.

Optional `tools:` in an agent's frontmatter restricts its tools (comma-separated);
the TOOLS table below is the older, per-name way and still applies when it is absent.

Dependency-free (no PyYAML) — parses the same simple frontmatter that
tests/lint-agents.py lints.
"""
import argparse
import re
import sys
from pathlib import Path

BRAIN = Path(__file__).resolve().parent.parent
MARKER = "by sync_agents.py"

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


def as_list(value) -> list:
    """A frontmatter value as a list: block list, inline [a, b], or a single scalar."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.startswith("["):
        return [v.strip().strip("'\"") for v in value.strip("[]").split(",") if v.strip()]
    return [value] if value else []


def build_subagent(src: Path, tier: str | None = None) -> tuple[str, str] | None:
    parsed = parse_agent(src.read_text(encoding="utf-8"))
    if not parsed:
        print(f"SKIP {src.name}: no frontmatter")
        return None
    fm, body = parsed
    tiers = as_list(fm.get("tiers"))
    if tier and tiers and tier not in tiers:
        return None
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
    tools = fm.get("tools") if isinstance(fm.get("tools"), str) else TOOLS.get(name)
    if tools:
        lines.append(f"tools: {tools}")
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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project-root", required=True, type=Path)
    ap.add_argument("--check", action="store_true",
                    help="verify outputs are up to date; write nothing")
    ap.add_argument("--namespace", default=None,
                    help="read agents/<namespace>/*.md instead of agents/*.md (comma-separated for several)")
    ap.add_argument("--tier", default=None, help="keep only agents whose tiers: list contains this tier")
    ap.add_argument("--prune", action="store_true", help="remove generated agents that are no longer selected")
    args = ap.parse_args()

    out_dir = args.project_root / ".claude" / "agents"
    src_dirs = ([BRAIN / "agents" / ns.strip() for ns in args.namespace.split(",") if ns.strip()]
                if args.namespace else [BRAIN / "agents"])
    sources = [src for d in src_dirs for src in sorted(d.glob("*.md"))]
    if not sources:
        print(f"FAIL: no agent definitions in {', '.join(str(d) for d in src_dirs)}")
        return 1

    stale, built_names = [], set()
    for src in sources:
        built = build_subagent(src, args.tier)
        if not built:
            continue
        name, content = built
        if name in built_names:
            print(f"FAIL: agent name {name!r} is defined twice across namespaces")
            return 1
        built_names.add(name)
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

    if args.prune and out_dir.is_dir():
        for existing in sorted(out_dir.glob("*.md")):
            if existing.stem in built_names or MARKER not in existing.read_text(encoding="utf-8"):
                continue
            if args.check:
                stale.append(existing)
                print(f"ORPHAN {existing}")
            else:
                existing.unlink()
                print(f"PRUNED {existing}")

    if args.check and stale:
        print(f"SYNC CHECK FAILED: {len(stale)} stale file(s) — re-run sync_agents.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
