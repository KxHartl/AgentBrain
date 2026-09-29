"""
AgentBrain thesis dashboard — one-screen status and consistency audit of a LiteRealm work.

    thesis.sh status     # progress: chapters, words, citations, figures, TODOs, pages, git
    thesis.sh audit      # the same, plus consistency checks; exit 1 on any FAIL

Reads docs/main.tex (following \\input / \\include), docs/references.bib,
data/sources/, .ai/config/project.yaml, STATE.md, data/EXPERIMENTS_LOG.md and git.

Audit FAILs: \\cite keys missing from the bib, bib `file` fields pointing at missing PDFs,
\\ref labels that are never defined, uncommitted or unpushed git work.
Audit WARNs: bib entries never cited, chapters with TODOs, sources without a bib entry,
PDF over max_pages.

Rebuilt 2026-09 from the interface the LiteRealm thesis helper calls; the original
was lost with the work disk (see RECOVERY.md).
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

INPUT_RE = re.compile(r"\\(?:input|include|subfile)\{([^}]+)\}")
CITE_RE = re.compile(r"\\(?:cite|citep|citet|parencite|textcite|autocite)\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|eqref|autoref|cref|Cref|pageref)\{([^}]+)\}")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
TODO_RE = re.compile(r"\\todo\b|\bTODO\b|\bFIXME\b|\bXXX\b|\?\?\?")
FIG_RE = re.compile(r"\\begin\{figure\*?\}")
TAB_RE = re.compile(r"\\begin\{table\*?\}")
BIB_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)(?=\n@|\Z)", re.S)
BIB_FILE_RE = re.compile(r"\bfile\s*=\s*[{\"]([^}\"]+)[}\"]", re.I)


def strip_comments(tex):
    return re.sub(r"(?<!\\)%.*", "", tex)


def word_count(tex):
    body = strip_comments(tex)
    body = re.sub(r"\\begin\{(equation|align|figure|table|tabular|tikzpicture|lstlisting)\*?\}.*?"
                  r"\\end\{\1\*?\}", " ", body, flags=re.S)
    body = re.sub(r"\$.*?\$", " ", body, flags=re.S)
    body = re.sub(r"\\[A-Za-z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", body)
    return len(re.findall(r"[A-Za-zČĆŠĐŽčćšđž]{2,}", body))


def read_yaml_scalars(path):
    """Top-level `key: value` pairs; enough for project.yaml without PyYAML."""
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r'^([A-Za-z_]+):\s*"?([^"#]*?)"?\s*(#.*)?$', line)
            if m:
                values[m.group(1)] = m.group(2).strip()
    return values


def included_files(main, docs):
    """main.tex and every file it pulls in, in document order."""
    seen, order = set(), []

    def walk(path):
        if path in seen or not path.exists():
            return
        seen.add(path)
        order.append(path)
        for ref in INPUT_RE.findall(strip_comments(path.read_text(encoding="utf-8", errors="replace"))):
            ref = ref.strip()
            candidates = [docs / ref, path.parent / ref]
            for c in list(candidates):
                if c.suffix != ".tex":
                    candidates.append(c.with_name(c.name + ".tex"))
            for c in candidates:
                if c.is_file():
                    walk(c.resolve())
                    break

    walk(main.resolve())
    return order


def parse_bib(bib):
    entries = {}
    if bib.exists():
        for kind, key, body in BIB_ENTRY_RE.findall(bib.read_text(encoding="utf-8", errors="replace")):
            if kind.lower() in ("comment", "string", "preamble"):
                continue
            f = BIB_FILE_RE.search(body)
            entries[key] = {"type": kind.lower(), "file": f.group(1).strip() if f else None}
    return entries


def git(root, *args):
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    except FileNotFoundError:
        return None


def pdf_pages(pdf):
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf)).pages)
    except Exception:  # noqa: BLE001 - pypdf missing or unreadable PDF
        return None


def collect(root, main_rel="docs/main.tex"):
    docs = root / "docs"
    cfg = read_yaml_scalars(root / ".ai" / "config" / "project.yaml")
    info = {"root": root, "cfg": cfg, "chapters": [], "cites": {}, "refs": set(), "labels": set(),
            "figures": 0, "tables": 0, "todos": 0}

    main = root / main_rel
    info["main"] = main if main.exists() else None
    files = included_files(main, docs) if main.exists() else sorted((docs / "chapters").glob("*.tex"))
    for f in files:
        tex = f.read_text(encoding="utf-8", errors="replace")
        body = strip_comments(tex)
        cites = [k.strip() for group in CITE_RE.findall(body) for k in group.split(",") if k.strip()]
        for k in cites:
            info["cites"].setdefault(k, set()).add(f)
        info["refs"].update(REF_RE.findall(body))
        info["labels"].update(LABEL_RE.findall(body))
        info["figures"] += len(FIG_RE.findall(body))
        info["tables"] += len(TAB_RE.findall(body))
        todos = len(TODO_RE.findall(tex))
        info["todos"] += todos
        if f != main.resolve():
            info["chapters"].append({"file": f, "words": word_count(tex), "cites": len(cites), "todos": todos})

    info["bib"] = parse_bib(docs / "references.bib")
    src = root / "data" / "sources"
    info["sources"] = sorted(p for p in src.rglob("*.pdf")) if src.exists() else []

    dist_version = cfg.get("dist_version") or "dev"
    pdfs = [root / "dist" / dist_version / "main.pdf", docs / "build" / "main.pdf", docs / "main.pdf"]
    pdf = next((p for p in pdfs if p.exists()), None)
    info["pdf"], info["pages"] = pdf, (pdf_pages(pdf) if pdf else None)

    log = root / "data" / "EXPERIMENTS_LOG.md"
    info["runs"] = sum(1 for line in log.read_text(encoding="utf-8").splitlines()
                       if line.startswith("| `RUN-") and "RUN-EXAMPLE" not in line) if log.exists() else 0

    state = root / "STATE.md"
    focus = None
    if state.exists():
        lines = state.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if re.match(r"^#+\s*(Trenutni fokus|Current focus)", line, re.I):
                focus = next((l.strip("-*> ").strip() for l in lines[i + 1:] if l.strip() and not l.startswith("#")), None)
                break
    info["focus"] = focus

    dirty = git(root, "status", "--porcelain")
    info["git_dirty"] = len(dirty.splitlines()) if dirty else 0
    ahead = git(root, "rev-list", "--count", "@{upstream}..HEAD")
    info["git_ahead"] = int(ahead) if ahead and ahead.isdigit() else None
    info["git_branch"] = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return info


def rel(root, p):
    try:
        return Path(p).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(p)


def print_status(info):
    root, cfg = info["root"], info["cfg"]
    title = cfg.get("thesis_title") or cfg.get("seminar_title") or cfg.get("name") or root.name
    print(f"== {title} ==  ({cfg.get('type', '?')}, {cfg.get('latex_format', '?')})")
    if info["focus"]:
        print(f"Focus: {info['focus']}")
    if not info["main"]:
        print("Root document not found - run latex_architect first (\"počni pisati\").")
    total = sum(c["words"] for c in info["chapters"])
    print(f"\nChapters ({len(info['chapters'])}, {total} words):")
    for c in info["chapters"]:
        flag = f"  TODO x{c['todos']}" if c["todos"] else ""
        print(f"  {rel(root, c['file']):<48} {c['words']:>6} w  {c['cites']:>3} cites{flag}")
    print(f"\nCitations: {len(info['cites'])} keys cited, {len(info['bib'])} in references.bib, "
          f"{len(info['sources'])} PDF(s) in data/sources/")
    print(f"Figures: {info['figures']}   Tables: {info['tables']}   TODOs: {info['todos']}   "
          f"Experiment runs: {info['runs']}")
    max_pages = info["cfg"].get("max_pages")
    if info["pdf"]:
        pages = info["pages"] if info["pages"] is not None else "?"
        print(f"PDF: {rel(root, info['pdf'])}, {pages} page(s)" + (f" / max {max_pages}" if max_pages else ""))
    else:
        print("PDF: not built yet (build-docs)")
    ahead = info["git_ahead"]
    print(f"Git: {info['git_branch']}, {info['git_dirty']} uncommitted, "
          f"{'no upstream' if ahead is None else f'{ahead} unpushed'}")


def audit(info, verbose=False):
    root = info["root"]
    fails, warns = [], []  # (category, message)
    bib = info["bib"]
    for key, files in sorted(info["cites"].items()):
        if key not in bib:
            where = ", ".join(sorted(rel(root, f) for f in files))
            fails.append(("cite", f"\\cite{{{key}}} has no entry in references.bib ({where})"))
    for key, entry in sorted(bib.items()):
        if entry["file"] and not (root / entry["file"]).exists():
            fails.append(("bibfile", f"bib entry {key}: file {entry['file']} does not exist"))
        if key not in info["cites"]:
            warns.append(("uncited", f"bib entry {key} is never cited"))
    for missing in sorted(info["refs"] - info["labels"]):
        fails.append(("ref", f"\\ref{{{missing}}} has no matching \\label"))
    linked = {Path(e["file"]).name for e in bib.values() if e["file"]}
    for pdf in info["sources"]:
        if pdf.name not in linked:
            warns.append(("nobib", f"{rel(root, pdf)} has no bib entry with file= (not citable yet)"))
    for c in info["chapters"]:
        if c["todos"]:
            warns.append(("todo", f"{rel(root, c['file'])}: {c['todos']} TODO(s)"))
    max_pages = info["cfg"].get("max_pages")
    if info["pages"] and max_pages and max_pages.isdigit() and info["pages"] > int(max_pages):
        warns.append(("pages", f"PDF has {info['pages']} pages, max_pages is {max_pages}"))
    if info["git_dirty"]:
        fails.append(("git", f"{info['git_dirty']} uncommitted change(s) (rule 1)"))
    if info["git_ahead"]:
        fails.append(("git", f"{info['git_ahead']} commit(s) not pushed - one disk failure from gone"))
    elif info["git_ahead"] is None and info["git_branch"] not in (None, "HEAD"):
        warns.append(("git", f"branch {info['git_branch']} has no upstream - is it pushed? (git push -u origin HEAD)"))

    print("\nAudit:")
    for label, items in (("WARN", warns), ("FAIL", fails)):
        shown = {}
        for cat, msg in items:
            shown[cat] = shown.get(cat, 0) + 1
            if verbose or shown[cat] <= 10:
                print(f"  {label}  {msg}")
        for cat, n in shown.items():
            if not verbose and n > 10:
                print(f"  {label}  ... and {n - 10} more like the above (--verbose shows all)")
    print(f"  {len(fails)} fail(s), {len(warns)} warning(s)")
    return 1 if fails else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Thesis status dashboard & audit.")
    parser.add_argument("command", nargs="?", choices=["status", "audit"], default="status")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--main", default="docs/main.tex", help="root document (default docs/main.tex)")
    parser.add_argument("--verbose", action="store_true", help="list every audit finding")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    info = collect(root, args.main)
    print_status(info)
    return audit(info, args.verbose) if args.command == "audit" else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
