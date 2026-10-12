#!/usr/bin/env python3
"""Lint agent definition frontmatter.

Every agents/*.md and agents/<namespace>/*.md must declare the required YAML frontmatter
keys so the routing contract stays intact. Optional `tiers:` may only name WorkRealm tiers,
and agent names must be unique within a namespace. Skills that opt into syncing with
`tiers:` must name valid tiers too. Dependency-free (no PyYAML).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from sync_agents import as_list, parse_agent  # noqa: E402

REQUIRED = ["name", "role", "triggers", "writes_to", "never_touches"]
TIERS = {"quick", "task", "project"}

fail = 0
agents = sorted((ROOT / "agents").rglob("*.md"))
if not agents:
    print("FAIL: no agent definitions found in agents/")
    sys.exit(1)

names: dict[tuple[str, str], Path] = {}
for md in agents:
    label = md.relative_to(ROOT / "agents").as_posix()
    text = md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        print(f"FAIL {label}: no YAML frontmatter")
        fail = 1
        continue
    keys = set(re.findall(r"^([a-z_]+):", m.group(1), re.M))
    missing = [k for k in REQUIRED if k not in keys]
    fm, _ = parse_agent(text)
    bad_tiers = [t for t in as_list(fm.get("tiers")) if t not in TIERS]
    key = (md.parent.name, fm.get("name", md.stem))
    if missing:
        print(f"FAIL {label}: missing {missing}")
        fail = 1
    elif bad_tiers:
        print(f"FAIL {label}: unknown tiers {bad_tiers} (allowed: {sorted(TIERS)})")
        fail = 1
    elif key in names:
        print(f"FAIL {label}: name {key[1]!r} already used by {names[key].name}")
        fail = 1
    else:
        names[key] = md
        print(f"OK   {label}")

for md in sorted((ROOT / "skills").glob("*.md")):
    parsed = parse_agent(md.read_text(encoding="utf-8"))
    bad = [t for t in as_list(parsed[0].get("tiers"))] if parsed else []
    bad = [t for t in bad if t not in TIERS]
    if bad:
        print(f"FAIL skills/{md.name}: unknown tiers {bad}")
        fail = 1

print("AGENT LINT: " + ("FAILED" if fail else "PASSED"))
sys.exit(fail)
