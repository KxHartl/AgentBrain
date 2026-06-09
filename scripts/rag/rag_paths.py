"""Shared LanceDB store-path resolution for the RAG ingest/query scripts.

Why this exists: LanceDB cannot commit a table on FAT/exFAT volumes. Lance writes
each manifest to a temp name and then copies it into place; on FAT/exFAT that copy
fails on Windows with ERROR_INVALID_FUNCTION ("Incorrect function", os error 1),
which aborts ingest right at create_table. PDF sources read fine from such volumes
-- only the vector store needs a "real" filesystem.

So when the natural in-project DB path (`<project>/.ai/rag/db`) lands on a volume
that can't host Lance, we transparently relocate the store to a per-project folder
under %LOCALAPPDATA% (or ~/.cache off Windows). Sources stay put; only the
generated, regenerable store moves. Set RAG_DB_DIR to force an explicit location.

ingest.py and query.py both resolve the store through here, so they always agree on
where the DB lives -- including after a relocation.
"""

import hashlib
import os
import sys
from pathlib import Path

# Filesystems that cannot host a LanceDB store (no atomic manifest commit).
_UNSUPPORTED_FS = {"FAT", "FAT12", "FAT16", "FAT32", "EXFAT"}


def enable_utf8_io():
    """Force UTF-8 stdout/stderr so non-Latin-1 content prints without crashing.

    PDF chunks routinely contain math symbols (theta, etc.), CJK, or accented text.
    The default Windows console encoding is cp1252, so printing such characters
    raises UnicodeEncodeError and aborts the run. Reconfiguring to UTF-8 with
    errors='replace' makes output robust everywhere. No-op if unsupported.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _windows_fs_name(path):
    """Filesystem name ('NTFS', 'exFAT', ...) for the volume holding `path`, on Windows.

    Returns None off Windows, or if detection fails for any reason -- callers treat
    None as "assume it's fine" so this can never break the common (NTFS/ext4) case.
    """
    if os.name != "nt":
        return None
    try:
        import ctypes

        drive = os.path.splitdrive(os.path.abspath(str(path)))[0]
        if not drive:
            return None
        root = drive + "\\"
        fs_buf = ctypes.create_unicode_buffer(261)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root), None, 0, None, None, None,
            fs_buf, ctypes.sizeof(fs_buf) // ctypes.sizeof(ctypes.c_wchar),
        )
        return fs_buf.value if ok else None
    except Exception:
        return None


def _fs_can_host_lance(path):
    name = _windows_fs_name(path)
    if name is None:
        return True  # non-Windows or undetectable -> assume supported
    return name.upper() not in _UNSUPPORTED_FS


def _relocated_db_dir(project_root):
    """Deterministic per-project store dir on a normal filesystem.

    Keyed by the absolute project path so ingest and query agree, and so two
    different projects never share one table.
    """
    project_root = Path(project_root).resolve()
    key = hashlib.sha1(str(project_root).encode("utf-8")).hexdigest()[:12]
    name = project_root.name or "project"
    base = os.environ.get("LOCALAPPDATA")
    base = Path(base) if base else (Path.home() / ".cache")
    return base / "AgentBrain" / "rag" / "{}-{}".format(name, key) / "db"


def resolve_store_dir(preferred, project_root=None, announce=False):
    """Return a store dir that can actually host LanceDB.

    Order of preference:
      1. RAG_DB_DIR env var, if set (explicit override -- used verbatim).
      2. `preferred`, unless it sits on a FAT/exFAT volume.
      3. A per-project folder under %LOCALAPPDATA% (the relocation fallback).

    `announce=True` prints a one-line notice to stderr when a relocation happens,
    so the user can see where the DB actually went (and how to override).
    """
    preferred = Path(preferred)

    override = os.environ.get("RAG_DB_DIR")
    if override:
        return Path(override).expanduser()

    if _fs_can_host_lance(preferred):
        return preferred

    target = _relocated_db_dir(project_root or Path.cwd())
    if announce:
        fs = _windows_fs_name(preferred) or "unsupported"
        print(
            "Note: {} is on a {} volume, which can't host a LanceDB store.\n"
            "      Using {} instead (set RAG_DB_DIR to override).".format(
                preferred, fs, target),
            file=sys.stderr,
        )
    return target
