#!/usr/bin/env python3
"""Lint agent definition frontmatter.

Every agents/*.md must declare the required YAML frontmatter keys so the routing
contract stays intact. Dependency-free (no PyYAML).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ["name", "role", "triggers", "writes_to", "never_touches"]

fail = 0
agents = sorted((ROOT / "agents").glob("*.md"))
if not agents:
    print("FAIL: no agent definitions found in agents/")
    sys.exit(1)

for md in agents:
    text = md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        print(f"FAIL {md.name}: no YAML frontmatter")
        fail = 1
        continue
    keys = set(re.findall(r"^([a-z_]+):", m.group(1), re.M))
    missing = [k for k in REQUIRED if k not in keys]
    if missing:
        print(f"FAIL {md.name}: missing {missing}")
        fail = 1
    else:
        print(f"OK   {md.name}")

print("AGENT LINT: " + ("FAILED" if fail else "PASSED"))
sys.exit(fail)
