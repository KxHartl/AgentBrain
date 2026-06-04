#!/usr/bin/env python3
"""
AgentBrain - Deterministic LaTeX template renderer.

Resolves the correct master template for a project's `latex_format`, fills the
metadata placeholders from `.ai/config/project.yaml`, and writes `docs/main.tex`.
This is the deterministic core that `latex_architect` wraps, so the
"never leave a {{PLACEHOLDER}}" rule is guaranteed by construction instead of by
hand-editing.

Usage:
    # Render the default format (read from project.yaml) into docs/main.tex
    python ~/.agentbrain/scripts/render_template.py --project-root .

    # Override format, also scaffold chapter stubs + references.bib + dirs
    python ~/.agentbrain/scripts/render_template.py --project-root . --format fsb-seminar --scaffold

    # Test mode: blank any remaining writer-content placeholders so the bare
    # template compiles (used by tests/compile-template.*)
    python ~/.agentbrain/scripts/render_template.py --project-root . --scaffold --fill-stubs

Exit codes: 0 ok, 1 usage/IO error, 2 validation error (missing required fields).
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

BRAIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FORMAT = "fsb-seminar"
REQUIRED_FIELDS = ("author_name", "course_name", "seminar_title", "professor_name")

# Writer-content placeholders are intentionally NOT filled here (writer's job).
# In --fill-stubs (test) mode they are blanked so the bare template compiles.
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_0-9]+)\}\}")


def parse_yaml_flat(path: Path) -> dict:
    """Minimal parser for the flat `key: "value"  # comment` project.yaml.

    Avoids a hard PyYAML dependency. Handles quoted/unquoted scalars, inline
    comments, and booleans. Good enough for project.yaml's flat structure.
    """
    cfg = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^([A-Za-z0-9_]+):\s*(.*)$', line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith('"'):
            # quoted string: take content up to the closing quote
            end = val.find('"', 1)
            val = val[1:end] if end != -1 else val[1:]
        else:
            # strip an inline comment from an unquoted scalar
            val = val.split("#", 1)[0].strip()
        cfg[key] = val
    return cfg


def as_bool(value) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def resolve_template(fmt: str) -> Path:
    """Return the master .tex file for a format.

    Globs `templates/<fmt>/latex/*.tex` rather than hardcoding the filename, so
    seminar.tex / thesis.tex / paper.tex / presentation.tex all resolve without
    a per-format special case (fixes the old hardcoded `seminar.tex` bug).
    """
    latex_dir = BRAIN_ROOT / "templates" / fmt / "latex"
    if not latex_dir.is_dir():
        raise FileNotFoundError(
            f"Format '{fmt}' has no LaTeX template at {latex_dir}"
        )
    tex_files = sorted(latex_dir.glob("*.tex"))
    if not tex_files:
        raise FileNotFoundError(f"No .tex master found in {latex_dir}")
    return tex_files[0]


def build_substitutions(cfg: dict) -> dict:
    """Map metadata placeholders -> values, with the documented fallbacks."""
    year = str(datetime.date.today().year)
    title = cfg.get("seminar_title") or cfg.get("name") or ""
    short = cfg.get("seminar_title_short") or title[:50]
    prof_title = cfg.get("professor_title", "").strip()
    prof_name = cfg.get("professor_name", "").strip()
    professor = f"{prof_title} {prof_name}".strip() if prof_name else \
        r"\colorbox{yellow}{\textbf{PROFESOR NIJE POSTAVLJEN}}"
    course = cfg.get("course_name") or "[KOLEGIJ NIJE POSTAVLJEN]"
    author = cfg.get("author_name") or "[IME NIJE POSTAVLJENO]"
    faculty = cfg.get("faculty") or \
        "Fakultet strojarstva i brodogradnje, Sveučilište u Zagrebu"

    lof = r"\listoffigures\clearpage" if as_bool(cfg.get("include_lof")) else ""
    lot = r"\listoftables\clearpage" if as_bool(cfg.get("include_lot")) else ""

    return {
        "KOLEGIJ": course,
        "NASLOV_SEMINARA": title,
        "NASLOV_SEMINARA_KRATKI": short,
        "NASLOV_RADA": title,
        "NASLOV_PREZENTACIJE": title,
        "KRATKI_NASLOV": short,
        "PODNASLOV": short,
        "PROFESOR": professor,
        "MENTORI": professor,
        "IME_I_PREZIME": author,
        "INSTITUCIJA": faculty,
        "EMAIL": cfg.get("email", ""),
        "DATUM": cfg.get("location_date") or f"Zagreb, {year}.",
        "GODINA": year,
        "LISTOFFIGURES": lof,
        "LISTOFTABLES": lot,
        "CHAPTER_INPUTS": "",
    }


def scaffold(docs: Path, rendered: str) -> None:
    """Ensure dirs, references.bib and any \\input{}-referenced stub files exist."""
    for d in ("chapters", "figures", "tables", "code"):
        (docs / d).mkdir(parents=True, exist_ok=True)
        gk = docs / d / ".gitkeep"
        if not any((docs / d).iterdir()):
            gk.write_text("", encoding="utf-8")

    bib = docs / "references.bib"
    if not bib.exists():
        bib.write_text(
            "% Auto-generated BibTeX database.\n"
            "% data_fetcher dodaje stavke; writer koristi \\cite{kljuc}.\n"
            "% @article{primjer2024, title={...}, author={...}, year={2024}}\n",
            encoding="utf-8",
        )

    for rel in re.findall(r"\\input\{([^}]+)\}", rendered):
        target = docs / (rel if rel.endswith(".tex") else rel + ".tex")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            name = target.stem
            target.write_text(
                f"% {name} — writer popunjava sadržaj.\n", encoding="utf-8"
            )


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a LaTeX master template.")
    ap.add_argument("--project-root", default=".", help="Project root directory.")
    ap.add_argument("--format", help="Override latex_format (else read from project.yaml).")
    ap.add_argument("--out", default="docs/main.tex", help="Output path (rel to project root).")
    ap.add_argument("--scaffold", action="store_true", help="Create chapter stubs, references.bib, dirs.")
    ap.add_argument("--fill-stubs", action="store_true", help="Blank remaining content placeholders (test mode).")
    ap.add_argument("--no-validate", action="store_true", help="Skip required-field validation.")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing main.tex.")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    cfg_path = root / ".ai" / "config" / "project.yaml"
    if not cfg_path.exists():
        print(f"ERROR: project.yaml not found at {cfg_path}", file=sys.stderr)
        return 1
    cfg = parse_yaml_flat(cfg_path)

    fmt = args.format or cfg.get("latex_format") or DEFAULT_FORMAT
    try:
        master = resolve_template(fmt)
    except FileNotFoundError as e:
        print(f"WARNING: {e}", file=sys.stderr)
        if fmt != DEFAULT_FORMAT:
            print(f"Falling back to '{DEFAULT_FORMAT}'.", file=sys.stderr)
            master = resolve_template(DEFAULT_FORMAT)
        else:
            return 1

    if not args.no_validate:
        missing = [f for f in REQUIRED_FIELDS if not cfg.get(f, "").strip()]
        if missing:
            print("ERROR: required project.yaml fields are empty:", file=sys.stderr)
            for f in missing:
                print(f"  - {f}", file=sys.stderr)
            print("Fill them in .ai/config/project.yaml before rendering.", file=sys.stderr)
            return 2

    out_path = root / args.out
    if out_path.exists() and not args.force:
        print(f"ERROR: {out_path} already exists. Use --force to overwrite.", file=sys.stderr)
        return 1

    text = master.read_text(encoding="utf-8")
    subs = build_substitutions(cfg)
    text = PLACEHOLDER_RE.sub(lambda m: subs.get(m.group(1), m.group(0)), text)

    if args.fill_stubs:
        # Blank any writer-content placeholders that remain, so the bare
        # template compiles in CI without real content.
        text = PLACEHOLDER_RE.sub("", text)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"Rendered {fmt} ({master.name}) -> {out_path}")

    if args.scaffold:
        scaffold(out_path.parent, text)
        print(f"Scaffolded chapter stubs / references.bib / dirs in {out_path.parent}")

    leftover = sorted(set(PLACEHOLDER_RE.findall(text)))
    if leftover and not args.fill_stubs:
        print("NOTE: writer-content placeholders left for writer to fill: "
              + ", ".join("{{" + p + "}}" for p in leftover))
    return 0


if __name__ == "__main__":
    sys.exit(main())
