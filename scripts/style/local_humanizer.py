"""
AgentBrain local humanizer — deterministic removal of AI filler phrases.

Applies the profile's `replacements` (defaults in style_common.DEFAULT_REPLACEMENTS)
case-insensitively, re-capitalises a sentence whose lead-in was deleted, and never
touches comments, math or command arguments it cannot see as prose. No LLM, no network:
what it changes is exactly what the replacement table says, shown as a diff.

Usage (via the project helper):
    style.sh humanize docs/chapters/01-uvod.tex              # print the diff only
    style.sh humanize docs/chapters/01-uvod.tex --in-place   # rewrite the file

Rebuilt 2026-09 from the contract in the LiteRealm style helper; the original was
lost with the work disk (see RECOVERY.md).
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from style_common import CLITICS, load_profile  # noqa: E402


def _match_case(original, replacement):
    if replacement and original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def humanize_line(line, replacements, manual):
    if line.lstrip().startswith("%"):
        return line, 0
    # Protect inline math and the tail comment from rewriting.
    cut = re.search(r"(?<!\\)%", line)
    code, tail = (line[:cut.start()], line[cut.start():]) if cut else (line, "")
    math = []

    def stash(m):
        math.append(m.group(0))
        return f"\x00{len(math) - 1}\x00"

    code = re.sub(r"(?<!\\)\$.*?(?<!\\)\$", stash, code)
    applied = []
    for phrase in sorted(replacements, key=len, reverse=True):
        rep = replacements[phrase]
        # Capture the word after the phrase: when a capitalised lead-in is deleted, that
        # word now starts the sentence (capitalise it) - unless it is a clitic, where only
        # reordering would fix the sentence; leave it for the author.
        pattern = re.compile(re.escape(phrase) + r"(\w*)", re.IGNORECASE)

        def sub(m, rep=rep):
            nxt = m.group(1)
            if not rep and nxt.lower() in CLITICS:
                manual.append(m.group(0).strip())
                return m.group(0)
            applied.append(phrase)
            if not rep and m.group(0)[:1].isupper():
                return nxt[:1].upper() + nxt[1:]
            return _match_case(m.group(0), rep) + nxt

        code = pattern.sub(sub, code)
    code = re.sub(r"\x00(\d+)\x00", lambda m: math[int(m.group(1))], code)
    return code + tail, len(applied)


def humanize_text(text, replacements, manual=None):
    manual = [] if manual is None else manual
    out, total = [], 0
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        new, n = humanize_line(body, replacements, manual)
        out.append(new + line[len(body):])
        total += n
    return "".join(out), total


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic AI-filler remover.")
    parser.add_argument("file")
    parser.add_argument("--in-place", action="store_true", help="rewrite the file")
    parser.add_argument("--profile", help="author profile path")
    args = parser.parse_args(argv)

    path = Path(args.file)
    if not path.is_file():
        print(f"Not found: {path}", file=sys.stderr)
        return 2
    original = path.read_text(encoding="utf-8")
    profile = load_profile(args.profile)
    manual = []
    new, n = humanize_text(original, profile["replacements"], manual)
    for phrase in manual:
        print(f"  manual: \"{phrase} ...\" - rephrase by hand (a clitic follows, word order must change)")
    if n == 0:
        print(f"{path}: nothing to change automatically.")
        return 0
    sys.stdout.writelines(difflib.unified_diff(original.splitlines(keepends=True), new.splitlines(keepends=True),
                                               fromfile=str(path), tofile=f"{path} (humanized)"))
    if args.in_place:
        path.write_text(new, encoding="utf-8")
        print(f"\n{path}: {n} replacement(s) written.")
    else:
        print(f"\n{path}: {n} replacement(s) proposed. Re-run with --in-place to apply.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
