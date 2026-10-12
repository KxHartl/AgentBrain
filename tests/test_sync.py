#!/usr/bin/env python3
"""Tests for scripts/sync_agents.py and scripts/sync_skills.py against a fixture brain.

    python tests/test_sync.py

Copies both scripts into a temporary brain, so the real agents/ and skills/ never shape
the results. Standard library only.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AGENT = """---
name: {name}
role: {name} role
{tiers}triggers:
  - "do {name}"
writes_to:
  - "notes/"
never_touches:
  - "sources/"
---

Body of {name}.
"""
SKILL = """---
domain: engineering
type: skill
author: test
{tiers}---
# {name}

## Context
Use {name} when testing.

## Solution
Steps.
"""


class SyncTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.brain, self.project = tmp / "brain", tmp / "project"
        (self.brain / "scripts").mkdir(parents=True)
        for script in ("sync_agents.py", "sync_skills.py"):
            shutil.copy2(ROOT / "scripts" / script, self.brain / "scripts" / script)
        self.project.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def agent(self, ns, name, tiers=None):
        path = self.brain / "agents" / ns / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(AGENT.format(name=name, tiers=f"tiers: {tiers}\n" if tiers else ""), encoding="utf-8")
        return path

    def skill(self, name, tiers=None):
        path = self.brain / "skills" / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SKILL.format(name=name, tiers=f"tiers: {tiers}\n" if tiers else ""), encoding="utf-8")
        return path

    def run_script(self, script, *args):
        return subprocess.run([sys.executable, str(self.brain / "scripts" / script),
                               "--project-root", str(self.project), *args], capture_output=True, text=True)

    def agents_out(self):
        return sorted(p.stem for p in (self.project / ".claude" / "agents").glob("*.md"))

    def test_tier_filter_and_untiered_agents(self):
        self.agent("work", "researcher", "[task, project]")
        self.agent("work", "lab_runner", "[project]")
        self.agent("work", "helper")  # no tiers: always synced
        self.assertEqual(self.run_script("sync_agents.py", "--namespace", "work", "--tier", "task").returncode, 0)
        self.assertEqual(self.agents_out(), ["helper", "researcher"])
        self.run_script("sync_agents.py", "--namespace", "work", "--tier", "project")
        self.assertEqual(self.agents_out(), ["helper", "lab_runner", "researcher"])

    def test_multiple_namespaces_and_duplicate_names(self):
        self.agent("work", "a")
        self.agent("shared", "b")
        self.assertEqual(self.run_script("sync_agents.py", "--namespace", "work,shared").returncode, 0)
        self.assertEqual(self.agents_out(), ["a", "b"])
        self.agent("shared", "a")
        self.assertNotEqual(self.run_script("sync_agents.py", "--namespace", "work,shared").returncode, 0)

    def test_prune_check_and_hand_written_agents(self):
        self.agent("work", "a")
        gone = self.agent("work", "b")
        self.run_script("sync_agents.py", "--namespace", "work")
        own = self.project / ".claude" / "agents" / "mine.md"
        own.write_text("---\nname: mine\n---\nhand-written\n", encoding="utf-8")
        gone.unlink()
        self.assertNotEqual(self.run_script("sync_agents.py", "--namespace", "work", "--prune", "--check").returncode, 0)
        self.run_script("sync_agents.py", "--namespace", "work", "--prune")
        self.assertEqual(self.agents_out(), ["a", "mine"])
        self.assertEqual(self.run_script("sync_agents.py", "--namespace", "work", "--prune", "--check").returncode, 0)

    def test_tools_frontmatter(self):
        path = self.agent("work", "reviewer")
        path.write_text(path.read_text(encoding="utf-8").replace("role:", "tools: Read, Grep\nrole:"), encoding="utf-8")
        self.run_script("sync_agents.py", "--namespace", "work")
        self.assertIn("tools: Read, Grep", (self.project / ".claude" / "agents" / "reviewer.md").read_text(encoding="utf-8"))

    def test_skills_opt_in_prune_and_keep_project_skills(self):
        self.skill("diagnose_bugs", "[task, project]")
        self.skill("arch", "[project]")
        self.skill("untagged")
        own = self.project / ".claude" / "skills" / "arch" / "SKILL.md"
        self.assertEqual(self.run_script("sync_skills.py", "--tier", "task").returncode, 0)
        out = self.project / ".claude" / "skills"
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["diagnose-bugs"])
        text = (out / "diagnose-bugs" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: diagnose-bugs\ndescription: Use diagnose_bugs when testing."))
        own.parent.mkdir(parents=True)
        own.write_text("---\nname: arch\ndescription: mine\n---\n", encoding="utf-8")
        self.run_script("sync_skills.py", "--tier", "project")
        self.assertIn("description: mine", own.read_text(encoding="utf-8"))  # never overwritten
        (self.brain / "skills" / "diagnose_bugs.md").unlink()
        self.assertNotEqual(self.run_script("sync_skills.py", "--tier", "project", "--prune", "--check").returncode, 0)
        self.run_script("sync_skills.py", "--tier", "project", "--prune")
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["arch"])


if __name__ == "__main__":
    unittest.main()
