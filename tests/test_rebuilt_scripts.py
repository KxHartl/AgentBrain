"""
Tests for the scripts rebuilt after the 2026-09 disk failure:
experiment_manager, style tools, thesis_dashboard, classify_source.

    python -m unittest discover -s tests -p "test_*.py"

Offline and fast: every test runs in a temporary LiteRealm-like project.
rag sync is covered end to end by tests/rag-roundtrip.sh (it needs embeddings).
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

BRAIN = Path(__file__).resolve().parents[1]
SCRIPTS = BRAIN / "scripts"
sys.path.insert(0, str(SCRIPTS / "style"))
sys.path.insert(0, str(SCRIPTS / "rag"))

import classify_source  # noqa: E402
import local_humanizer  # noqa: E402
import style_common  # noqa: E402


def run(script, *args, cwd):
    env = {**os.environ, "AGENTBRAIN_PATH": str(BRAIN)}
    return subprocess.run([sys.executable, str(script), *args], cwd=cwd, env=env,
                          capture_output=True, text=True, encoding="utf-8")


class TempProject(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for d in ("data/raw", "data/processed", "data/sources", "docs/chapters", "src", ".ai/config"):
            (self.root / d).mkdir(parents=True)
        (self.root / ".ai/config/project.yaml").write_text(
            'name: "T"\ntype: "thesis"\nmax_pages: 5\ndist_version: "dev"\n', encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()


class ExperimentManagerTest(TempProject):
    EM = SCRIPTS / "data" / "experiment_manager.py"

    def new_run(self):
        r = run(self.EM, "new", "--type", "exp", "--name", "Motor Torque", "--desc", "step",
                "--project-root", ".", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        runs = [p for p in (self.root / "data/raw").iterdir() if p.is_dir()]
        self.assertEqual(len(runs), 1)
        return runs[0]

    def test_new_creates_manifest_and_log_row(self):
        run_dir = self.new_run()
        self.assertTrue(run_dir.name.endswith("_exp_motor-torque"))
        self.assertTrue((run_dir / "manifest.yaml").exists())
        log = (self.root / "data/EXPERIMENTS_LOG.md").read_text(encoding="utf-8")
        self.assertIn(f"`{run_dir.name}`", log)

    def test_process_records_provenance_and_audit_catches_changed_raw(self):
        run_dir = self.new_run()
        (run_dir / "d.csv").write_text("t,v\n0,1\n", encoding="utf-8")
        (self.root / "src/proc.py").write_text(textwrap.dedent("""
            import argparse, pathlib
            a = argparse.ArgumentParser(); a.add_argument("--raw"); a.add_argument("--out")
            x = a.parse_args(); pathlib.Path(x.out, "mean.txt").write_text("1")
        """), encoding="utf-8")
        r = run(self.EM, "--project-root", ".", "process", "--raw", run_dir.name,
                "--script", "src/proc.py", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        outs = list((self.root / "data/processed").glob("*/mean.txt"))
        self.assertEqual(len(outs), 1)
        self.assertIn("Valid", (self.root / "data/EXPERIMENTS_LOG.md").read_text(encoding="utf-8"))
        self.assertEqual(run(self.EM, "audit", "--project-root", ".", cwd=self.root).returncode, 0)

        (run_dir / "d.csv").write_text("t,v\n0,2\n", encoding="utf-8")
        r = run(self.EM, "audit", "--project-root", ".", cwd=self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("changed since processing", r.stdout)


class StyleTest(unittest.TestCase):
    def test_tex_to_prose_drops_markup_math_and_comments(self):
        prose = style_common.tex_to_prose(
            "\\section{Uvod}\nTekst \\emph{bitan} $x=1$ \\cite{k}. % komentar\n"
            "\\begin{equation}a=b\\end{equation}\nDrugi.")
        self.assertNotIn("komentar", prose)
        self.assertNotIn("\\", prose)
        self.assertIn("bitan", prose)

    def test_split_keeps_abbreviations_together(self):
        s = style_common.split_sentences("Sustav, npr. robot, radi. Kratko. Zašto? Jer.")
        self.assertEqual(s[0], "Sustav, npr. robot, radi.")
        self.assertEqual(len(s), 4)

    def test_filler_lowers_the_score(self):
        profile = style_common.load_profile("/nonexistent/profile.yaml")
        clean = "Robot umeće utikač. Sila raste do 80 N. Tada kontroler popušta i utikač sjeda u utičnicu bez udara."
        filler = "Ključno je napomenuti da robot umeće utikač. U današnje vrijeme sila igra ključnu ulogu."
        import check_style
        def score_of(text):
            m = style_common.metrics(style_common.split_sentences(text))
            return check_style.score(m, style_common.find_phrases(text, profile["forbidden_phrases"]), profile)[0]
        self.assertGreater(score_of(clean), score_of(filler))

    def test_humanizer_capitalises_and_skips_clitics(self):
        reps = style_common.DEFAULT_REPLACEMENTS
        new, n = local_humanizer.humanize_text("Važno je napomenuti da robot radi. $x$ ostaje.\n", reps)
        self.assertEqual(new, "Robot radi. $x$ ostaje.\n")
        self.assertEqual(n, 1)
        manual = []
        new, n = local_humanizer.humanize_text("Ključno je napomenuti da je sustav gotov.\n", reps, manual)
        self.assertEqual(n, 0)
        self.assertEqual(new, "Ključno je napomenuti da je sustav gotov.\n")
        self.assertTrue(manual)

    def test_humanizer_leaves_comments_alone(self):
        new, n = local_humanizer.humanize_text("Tekst. % važno je napomenuti da x\n",
                                               style_common.DEFAULT_REPLACEMENTS)
        self.assertEqual(n, 0)


class ThesisDashboardTest(TempProject):
    TD = SCRIPTS / "thesis_dashboard.py"

    def write_docs(self, cite="a", label="fig:x", ref="fig:x"):
        (self.root / "docs/main.tex").write_text(
            "\\documentclass{article}\\begin{document}\\input{chapters/01-uvod}\\end{document}",
            encoding="utf-8")
        (self.root / "docs/chapters/01-uvod.tex").write_text(
            f"Tekst o robotu \\cite{{{cite}}}. Vidi \\ref{{{ref}}}.\n"
            f"\\begin{{figure}}\\label{{{label}}}\\end{{figure}}\n", encoding="utf-8")
        (self.root / "docs/references.bib").write_text(
            "@article{a,\n  title={A},\n  file={data/sources/a.pdf}\n}\n", encoding="utf-8")
        (self.root / "data/sources/a.pdf").write_bytes(b"%PDF-1.4\n")

    def test_status_reads_included_chapters(self):
        self.write_docs()
        r = run(self.TD, "status", "--project-root", ".", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("chapters/01-uvod.tex", r.stdout)
        self.assertIn("1 keys cited", r.stdout)

    def test_audit_passes_then_fails_on_missing_key_and_label(self):
        self.write_docs()
        self.assertEqual(run(self.TD, "audit", "--project-root", ".", cwd=self.root).returncode, 0)
        self.write_docs(cite="missing", ref="fig:none")
        r = run(self.TD, "audit", "--project-root", ".", cwd=self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("\\cite{missing}", r.stdout)
        self.assertIn("\\ref{fig:none}", r.stdout)


class ClassifySourceTest(unittest.TestCase):
    def test_rules(self):
        cases = {
            "reg_2018_545_32018R0545_en.pdf": ("Commission Implementing Regulation (EU) 2018/545", "regulations"),
            "iso_12100_2010.pdf": ("This International Standard specifies ... Normative references", "standards"),
            "arxiv_2021_inlet_detection.pdf": ("Abstract ... arXiv:2101.00001 ... et al.", "papers"),
            "hartl_diplomski.pdf": ("DIPLOMSKI RAD ... Mentor:", "theses"),
            "notes.pdf": ("", "other"),
        }
        for name, (text, want) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(classify_source.classify(name, text=text)["category"], want)

    def test_apply_only_sorts_loose_staging_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp) / "data" / "staging"
            staging.mkdir(parents=True)
            pdf = staging / "reg_2018_545_32018R0545_en.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            elsewhere = Path(tmp) / "reg_2019_1_x.pdf"
            elsewhere.write_bytes(b"%PDF-1.4\n")
            self.assertEqual(classify_source.main([str(pdf), str(elsewhere), "--apply"]), 0)
            self.assertTrue((staging / "regulations" / pdf.name).exists())
            self.assertTrue(elsewhere.exists())


if __name__ == "__main__":
    unittest.main()
