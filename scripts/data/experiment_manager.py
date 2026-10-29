"""
AgentBrain — Experiment & research data manager (FAIR, traceable runs).

Every measurement, simulation or benchmark gets one raw folder with a manifest,
every derived result one processed folder with a provenance record, and one row
in data/EXPERIMENTS_LOG.md — so each figure in the thesis traces back to its raw data.

Usage (via the project helper, which adds --project-root .):
    experiment.sh new --type exp --name motor-torque --desc "Step response"
    experiment.sh process --raw 2026-08-20_143000_exp_motor-torque --script src/processing/filter.py
    experiment.sh list
    experiment.sh audit

Layout:
    data/raw/<YYYY-MM-DD_HHMMSS>_<type>_<slug>/manifest.yaml      (+ the raw files you add)
    data/processed/<type>_<slug>_<ddmmyyyy_hhmmss>/provenance.yaml (+ script outputs)

`process --script` runs:  python <script> --raw <raw_dir> --out <processed_dir>
Raw folders are append-only (LiteRealm rule 2): this tool never modifies a file in
data/raw/ except the manifest of a run it has just created.

Rebuilt 2026-09 from the interface the LiteRealm helpers and the data_engineer agent
call; the original was lost unpushed with the work disk (see RECOVERY.md).
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TYPES = ("exp", "sim", "bench", "acq")
LOG_NAME = "EXPERIMENTS_LOG.md"
LOG_HEADER = (
    "# Registar eksperimenata i mjerenja (Experiments Log)\n\n"
    "Središnji registar svih eksperimentalnih mjerenja, numeričkih simulacija i prikupljanja podataka.\n"
    "Svaki redak odgovara jednoj mapi u `data/raw/` i povezanim obrađenim podacima u `data/processed/`.\n\n"
    "| ID | Datum & Vrijeme | Tip | Naziv i opis | Sirovi podaci (`data/raw/`) | "
    "Obrađeni podaci (`data/processed/`) | Poglavlje / Slika | Status |\n"
    "|---|---|---|---|---|---|---|---|\n"
)
STATUS_RAW = "🟡 Raw"
STATUS_VALID = "🟢 Valid"
STATUS_FAILED = "🔴 Failed"
RAW_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{6})_(exp|sim|bench|acq)_(.+)$")
MANIFEST_REQUIRED = ("id", "type", "name", "description", "created")
MANIFEST_TO_FILL = ("operator", "conditions", "devices", "sampling_rate_hz")


# --- small helpers ----------------------------------------------------------

def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "run"


def dump_yaml(data, path):
    """Write YAML with PyYAML when present; JSON otherwise (JSON is valid YAML)."""
    try:
        import yaml
        text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    except ImportError:
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    Path(path).write_text(text, encoding="utf-8")


def load_yaml(path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        return json.loads(text)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(root, *args):
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return out.stdout.strip() if out.returncode == 0 else ""
    except FileNotFoundError:
        return ""


def raw_files(run_dir):
    """Data files of a raw run (everything but the manifest), relative to the run."""
    return sorted(p.relative_to(run_dir).as_posix() for p in run_dir.rglob("*")
                  if p.is_file() and p.name not in ("manifest.yaml", ".gitkeep"))


# --- experiments log --------------------------------------------------------

def log_path(root):
    return root / "data" / LOG_NAME


def read_log(root):
    path = log_path(root)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(LOG_HEADER, encoding="utf-8")
    return path.read_text(encoding="utf-8")


def append_log_row(root, cells):
    text = read_log(root)
    if not text.endswith("\n"):
        text += "\n"
    text += "| " + " | ".join(cells) + " |\n"
    log_path(root).write_text(text, encoding="utf-8")


def update_log_row(root, run_id, processed=None, status=None):
    """Fill the processed column / status of the row whose ID cell is `run_id`."""
    lines = read_log(root).splitlines(keepends=True)
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 8 and cells[0].strip("`") == run_id:
            if processed:
                existing = [c for c in cells[5].split("<br>") if c and c != "—"]
                if f"`{processed}`" not in existing:
                    existing.append(f"`{processed}`")
                cells[5] = "<br>".join(existing)
            if status:
                cells[7] = status
            lines[i] = "| " + " | ".join(cells) + " |\n"
            log_path(root).write_text("".join(lines), encoding="utf-8")
            return True
    return False


def logged_ids(root):
    ids = set()
    for line in read_log(root).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 8 and cells[0].startswith("`"):
            ids.add(cells[0].strip("`"))
    return ids


def run_id_for(folder_name):
    m = RAW_RE.match(folder_name)
    if not m:
        return None
    return f"RUN-{m.group(1).replace('-', '')}-{m.group(2)}"


# --- commands ---------------------------------------------------------------

def cmd_new(root, args):
    now = dt.datetime.now()
    slug = slugify(args.name)
    folder = f"{now:%Y-%m-%d_%H%M%S}_{args.type}_{slug}"
    run_dir = root / "data" / "raw" / folder
    if run_dir.exists():
        sys.exit(f"Already exists: {run_dir.relative_to(root)}")
    run_dir.mkdir(parents=True)
    run_id = run_id_for(folder)
    manifest = {
        "id": run_id,
        "type": args.type,
        "name": slug,
        "description": args.desc,
        "created": now.isoformat(timespec="seconds"),
        "operator": git(root, "config", "user.name") or "",
        # Fill these before committing the raw data: the folder is append-only after that.
        "conditions": {},
        "devices": [],
        "sampling_rate_hz": None,
        "notes": "",
    }
    dump_yaml(manifest, run_dir / "manifest.yaml")
    append_log_row(root, [f"`{run_id}`", f"{now:%Y-%m-%d %H:%M}", args.type.upper(),
                          f"{slug}: {args.desc}", f"`{folder}`", "—", "—", STATUS_RAW])
    print(f"Created data/raw/{folder}/")
    print(f"  manifest.yaml  -> fill conditions, devices, sampling_rate_hz before the first commit")
    print(f"  {LOG_NAME} row {run_id} added")
    return 0


def resolve_raw(root, name):
    raw_dir = root / "data" / "raw" / Path(name).name
    if not raw_dir.is_dir():
        sys.exit(f"No raw run: data/raw/{Path(name).name}")
    return raw_dir


def cmd_process(root, args):
    raw_dir = resolve_raw(root, args.raw)
    m = RAW_RE.match(raw_dir.name)
    if not m:
        sys.exit(f"Not a managed run folder (expected YYYY-MM-DD_HHMMSS_<type>_<slug>): {raw_dir.name}")
    now = dt.datetime.now()
    out_name = f"{m.group(3)}_{args.name or m.group(4)}_{now:%d%m%Y_%H%M%S}"
    out_dir = root / "data" / "processed" / out_name
    out_dir.mkdir(parents=True)

    provenance = {
        "raw": raw_dir.name,
        "run_id": run_id_for(raw_dir.name),
        "created": now.isoformat(timespec="seconds"),
        "raw_files": {f: sha256(raw_dir / f) for f in raw_files(raw_dir)},
        "git_commit": git(root, "rev-parse", "--short", "HEAD"),
        "python": sys.version.split()[0],
    }
    status, rc = STATUS_VALID, 0
    if args.script:
        script = (root / args.script).resolve()
        if not script.is_file():
            sys.exit(f"No such script: {args.script}")
        provenance["script"] = {"path": script.relative_to(root).as_posix(), "sha256": sha256(script)}
        cmd = [sys.executable, str(script), "--raw", str(raw_dir), "--out", str(out_dir)]
        print("Running:", " ".join(cmd))
        rc = subprocess.run(cmd, cwd=root).returncode
        provenance["exit_code"] = rc
        if rc != 0:
            status = STATUS_FAILED
    else:
        provenance["script"] = None
        provenance["notes"] = "Manual processing: describe the steps here."
    provenance["outputs"] = sorted(p.relative_to(out_dir).as_posix() for p in out_dir.rglob("*")
                                   if p.is_file() and p.name != "provenance.yaml")
    dump_yaml(provenance, out_dir / "provenance.yaml")

    if not update_log_row(root, provenance["run_id"], processed=out_name, status=status):
        print(f"  WARNING: {provenance['run_id']} not found in {LOG_NAME}; add the row by hand.")
    print(f"Created data/processed/{out_name}/ ({len(provenance['outputs'])} output file(s)), status {status}")
    return rc


def processed_index(root):
    """raw folder name -> list of processed folder names (from provenance)."""
    index = {}
    base = root / "data" / "processed"
    for prov in sorted(base.glob("*/provenance.yaml")) if base.exists() else []:
        try:
            raw = load_yaml(prov).get("raw")
        except Exception:  # noqa: BLE001
            continue
        index.setdefault(raw, []).append(prov.parent.name)
    return index


def managed_runs(root):
    base = root / "data" / "raw"
    return sorted(p for p in base.iterdir() if p.is_dir() and RAW_RE.match(p.name)) if base.exists() else []


def cmd_list(root, _args):
    runs = managed_runs(root)
    if not runs:
        print("No runs yet. Start one with: experiment new --type exp --name <slug> --desc \"...\"")
        return 0
    index = processed_index(root)
    for run in runs:
        files = raw_files(run)
        procs = index.get(run.name, [])
        print(f"{run_id_for(run.name)}  {run.name}")
        print(f"    raw files: {len(files)}   processed: {', '.join(procs) if procs else '—'}")
    return 0


def cmd_audit(root, _args):
    problems, warnings = [], []
    ids = logged_ids(root)
    for run in managed_runs(root):
        rel = f"data/raw/{run.name}"
        manifest_path = run / "manifest.yaml"
        if not manifest_path.exists():
            problems.append(f"{rel}: no manifest.yaml")
            continue
        manifest = load_yaml(manifest_path)
        for key in MANIFEST_REQUIRED:
            if not manifest.get(key):
                problems.append(f"{rel}: manifest field '{key}' is empty")
        for key in MANIFEST_TO_FILL:
            if manifest.get(key) in (None, "", {}, []):
                warnings.append(f"{rel}: manifest field '{key}' not filled")
        if not raw_files(run):
            warnings.append(f"{rel}: no data files yet")
        if run_id_for(run.name) not in ids:
            problems.append(f"{rel}: no row {run_id_for(run.name)} in data/{LOG_NAME}")

    base = root / "data" / "processed"
    for out in sorted(p for p in base.iterdir() if p.is_dir()) if base.exists() else []:
        rel = f"data/processed/{out.name}"
        prov_path = out / "provenance.yaml"
        if not prov_path.exists():
            warnings.append(f"{rel}: no provenance.yaml (not created by experiment process)")
            continue
        prov = load_yaml(prov_path)
        raw_dir = root / "data" / "raw" / str(prov.get("raw"))
        if not raw_dir.is_dir():
            problems.append(f"{rel}: raw run '{prov.get('raw')}' does not exist")
            continue
        for f, digest in (prov.get("raw_files") or {}).items():
            if not (raw_dir / f).exists():
                problems.append(f"{rel}: raw file {f} is gone")
            elif sha256(raw_dir / f) != digest:
                problems.append(f"{rel}: raw file {f} changed since processing")
        script = prov.get("script")
        if script and (root / script["path"]).exists() and sha256(root / script["path"]) != script["sha256"]:
            warnings.append(f"{rel}: {script['path']} changed since this run (re-run to refresh)")

    for w in warnings:
        print(f"  WARN  {w}")
    for p in problems:
        print(f"  FAIL  {p}")
    runs = len(managed_runs(root))
    print(f"Audit: {runs} run(s), {len(problems)} problem(s), {len(warnings)} warning(s).")
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Experiment & research data manager.")
    parser.add_argument("--project-root", default=".", help="LiteRealm project root (default: cwd)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="create a raw run folder + manifest + log row")
    p_new.add_argument("--type", choices=TYPES, required=True)
    p_new.add_argument("--name", required=True)
    p_new.add_argument("--desc", default="")

    p_proc = sub.add_parser("process", help="create a processed folder with provenance")
    p_proc.add_argument("--raw", required=True, help="raw run folder name")
    p_proc.add_argument("--script", help="script run as: python <script> --raw <dir> --out <dir>")
    p_proc.add_argument("--name", help="slug for the processed folder (default: the run's slug)")

    sub.add_parser("list", help="list runs and their processed outputs")
    sub.add_parser("audit", help="check manifests, provenance, log rows and raw integrity")

    # The helpers append --project-root after the sub-command; accept it anywhere.
    for p in sub.choices.values():
        p.add_argument("--project-root", dest="project_root_sub", default=None, help=argparse.SUPPRESS)

    args = parser.parse_args(argv)
    root = Path(args.project_root_sub or args.project_root).resolve()
    if not (root / "data").is_dir() and args.command != "new":
        sys.exit(f"No data/ folder in {root} - run from a LiteRealm project root.")
    handler = {"new": cmd_new, "process": cmd_process, "list": cmd_list, "audit": cmd_audit}[args.command]
    return handler(root, args)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
