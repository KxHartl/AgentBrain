#!/usr/bin/env python3
"""Sync AgentBrain skills into a project's Claude Code skills.

Source of truth stays in ~/.agentbrain/skills/*.md (the _TEMPLATE.md format:
domain/type/author frontmatter, Context / Solution / Gotchas sections). A skill is
synced only when it opts in with a `tiers:` list; it then becomes
<project>/.claude/skills/<name>/SKILL.md, with `name` (file stem, '_' -> '-') and
`description` (the skill's `description:` field, else its Context paragraph) so Claude
can load it when relevant or on /<name>.

Usage:
    python ~/.agentbrain/scripts/sync_skills.py --project-root . --tier task [--prune] [--check]

--tier T selects skills whose `tiers:` contains T (WorkRealm tiers: quick, task, project).
--prune removes generated skills (SKILL.md carrying this script's marker) that are no
longer selected. A skill folder without the marker is the project's own and is never
overwritten or removed.

Dependency-free (no PyYAML).
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_agents import as_list, parse_agent  # noqa: E402  same frontmatter dialect

BRAIN = Path(__file__).resolve().parent.parent
MARKER = "by sync_skills.py"
MAX_DESCRIPTION = 1000


def describe(fm: dict, body: str) -> str:
    if isinstance(fm.get("description"), str) and fm["description"]:
        return fm["description"]
    m = re.search(r"^## Context\s*\n+(.+?)(?:\n\s*\n|\n#|$)", body, re.S | re.M)
    text = m.group(1) if m else body
    return " ".join(text.split())[:MAX_DESCRIPTION]


def build_skill(src: Path, tier: str) -> tuple[str, str] | None:
    parsed = parse_agent(src.read_text(encoding="utf-8"))
    if not parsed:
        return None
    fm, body = parsed
    if tier not in as_list(fm.get("tiers")):
        return None
    name = src.stem.replace("_", "-").lower()
    description = describe(fm, body).replace("\n", " ")
    content = "\n".join([
        "---",
        f"name: {name}",
        f"description: {description}",
        "---",
        "",
        f"<!-- AUTO-GENERATED from ~/.agentbrain/skills/{src.name} {MARKER}. Edit there, then re-run the sync. -->",
        "",
        body,
        "",
    ])
    return name, content


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project-root", required=True, type=Path)
    ap.add_argument("--tier", required=True, help="sync skills whose tiers: list contains this tier")
    ap.add_argument("--check", action="store_true", help="verify outputs are up to date; write nothing")
    ap.add_argument("--prune", action="store_true", help="remove generated skills that are no longer selected")
    args = ap.parse_args()

    out_dir = args.project_root / ".claude" / "skills"
    stale, built_names = [], set()
    for src in sorted((BRAIN / "skills").glob("*.md")):
        built = build_skill(src, args.tier)
        if not built:
            continue
        name, content = built
        built_names.add(name)
        dest = out_dir / name / "SKILL.md"
        if dest.exists() and MARKER not in dest.read_text(encoding="utf-8"):
            print(f"KEEP  {dest} (project's own skill; not overwritten)")
            continue
        if args.check:
            if not dest.exists() or dest.read_text(encoding="utf-8") != content:
                stale.append(dest)
                print(f"STALE {dest}")
            else:
                print(f"OK    {name}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8", newline="\n")
            print(f"WROTE {dest}")

    if args.prune and out_dir.is_dir():
        for skill in sorted(out_dir.glob("*/SKILL.md")):
            if skill.parent.name in built_names or MARKER not in skill.read_text(encoding="utf-8"):
                continue
            if args.check:
                stale.append(skill)
                print(f"ORPHAN {skill}")
            else:
                shutil.rmtree(skill.parent)
                print(f"PRUNED {skill.parent}")

    if args.check and stale:
        print(f"SYNC CHECK FAILED: {len(stale)} stale skill(s) — re-run sync_skills.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
