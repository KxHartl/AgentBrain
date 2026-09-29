"""
LiteRealm RAG — classify a source document into a staging/sources category.

Keyword rules over the file name and the first pages' text (pypdf when available):
standards, regulations, papers, theses, datasheets, books, reports, other.
The category is the folder name used in data/staging/<category>/ and
data/sources/<category>/ (and the chunk `domain` in rag sync).

    rag.sh classify data/staging/new.pdf [more.pdf | a folder ...]
    rag.sh classify data/staging/ --json
    rag.sh classify data/staging/ --apply     # move loose files in data/staging/ into their category

--apply only ever moves files that sit directly in data/staging/ (the data_fetcher
area); data/sources/ is promoted by the user with promote-sources.

Rebuilt 2026-09 from the interface the LiteRealm rag helper calls (`rag classify`);
the original was lost with the work disk (see RECOVERY.md).
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

RULES = {
    "standards": [
        (r"\b(EN|ISO|IEC|HRN|DIN|BS|ASTM|UIC|SAE)[\s_-]?(EN[\s_-]?)?\d{3,5}", 3),
        (r"\bIEEE\s+Std\b", 3), (r"\bnormative references\b", 2), (r"\bnorma\b", 1),
        (r"\bthis (international )?standard\b", 2), (r"\bICS\s+\d", 2), (r"\bprEN\b", 2),
    ],
    "regulations": [
        (r"\bRegulation \((EU|EC)\)", 3), (r"\bDirective\s+(\(EU\)\s+)?\d{2,4}/\d+", 3),
        (r"\bCommission (Implementing|Delegated)\b", 3), (r"\bOfficial Journal\b", 2),
        (r"\bTSI\b", 2), (r"\bUredb[aeu]\b", 3), (r"\bDirektiv[aeu]\b", 2), (r"\bNarodne novine\b", 3),
        (r"\bPravilnik\b", 2), (r"\bZakon o\b", 2), (r"\bERA\b", 1), (r"\beur-lex\b", 2),
    ],
    "papers": [
        (r"\bdoi\.org/|\bdoi:\s*10\.|\b10\.\d{4,9}/", 3), (r"\babstract\b", 2), (r"\bkeywords?\b", 1),
        (r"\bjournal\b", 1), (r"\bproceedings\b", 2), (r"\barxiv\b", 3), (r"\bet al\.", 1),
        (r"\bconference\b", 1), (r"\bIEEE (Transactions|Access|Robotics)\b", 2),
    ],
    "theses": [
        (r"\b(diplomski|završni|doktorski|magistarski) rad\b", 4), (r"\bmaster'?s thesis\b", 4),
        (r"\b(phd |doctoral )?dissertation\b", 3), (r"\bmentor\b", 1), (r"\bbachelor'?s thesis\b", 4),
    ],
    "datasheets": [
        (r"\bdata ?sheet\b", 3), (r"\btechnical data\b", 2), (r"\btehnički podaci\b", 2),
        (r"\b(user|installation|operating|service) (manual|instructions)\b", 3), (r"\bpriručnik\b", 2),
        (r"\bspecifications?\b", 1), (r"\border(ing)? (code|number)\b", 2),
    ],
    "books": [
        (r"\bISBN\b", 3), (r"\bpreface\b|\bpredgovor\b", 2), (r"\b(\d+(st|nd|rd|th)|second|third) edition\b", 2),
        (r"\bizdanje\b", 1), (r"\btable of contents\b|\bsadržaj\b", 1), (r"\bchapter \d+\b", 1),
    ],
    "reports": [
        (r"\bwhite ?paper\b", 3), (r"\btechnical report\b", 3), (r"\bposition paper\b", 3),
        (r"\bizvješće\b|\bizvještaj\b", 2), (r"\breport\b", 1), (r"\bexecutive summary\b", 2),
    ],
}
CATEGORIES = list(RULES) + ["other"]


def first_pages_text(path, pages=2):
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join((reader.pages[i].extract_text() or "") for i in range(min(pages, len(reader.pages))))
    except Exception:  # noqa: BLE001 - pypdf missing, encrypted or broken PDF
        return ""


def classify(path, text=None):
    """{'file', 'category', 'confidence', 'reasons'} for one document."""
    path = Path(path)
    name = re.sub(r"[_\-.]+", " ", path.stem)
    body = first_pages_text(path) if text is None else text
    scores, reasons = {}, {}
    for cat, rules in RULES.items():
        for pattern, weight in rules:
            rx = re.compile(pattern, re.IGNORECASE)
            hits = 0
            if rx.search(name):
                hits += 2 * weight  # the file name is a strong signal (staging names are chosen)
            if body and rx.search(body):
                hits += weight
            if hits:
                scores[cat] = scores.get(cat, 0) + hits
                reasons.setdefault(cat, []).append(pattern)
    if not scores:
        return {"file": str(path), "category": "other", "confidence": 0.0,
                "reasons": ["no rule matched" + ("" if body else " (no extractable text)")]}
    best = max(scores, key=scores.get)
    confidence = round(scores[best] / sum(scores.values()), 2)
    return {"file": str(path), "category": best, "confidence": confidence,
            "reasons": reasons[best][:4], "scores": scores}


def expand(targets):
    for t in targets:
        p = Path(t)
        if p.is_dir():
            yield from sorted(x for x in p.glob("*.pdf"))
        elif p.is_file():
            yield p
        else:
            print(f"Not found: {t}", file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Classify source documents into categories.")
    parser.add_argument("targets", nargs="+", help="PDF files or folders (non-recursive)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--apply", action="store_true",
                        help="move loose files in data/staging/ into data/staging/<category>/")
    args = parser.parse_args(argv)

    results = [classify(p) for p in expand(args.targets)]
    if not results:
        return 1
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print(f"{r['category']:<12} {r['confidence']:.2f}  {r['file']}")
    if args.apply:
        for r in results:
            src = Path(r["file"]).resolve()
            if src.parent.name != "staging" or src.parent.parent.name != "data":
                print(f"  skip (not a loose file in data/staging/): {r['file']}")
                continue
            dest = src.parent / r["category"] / src.name
            if dest.exists():
                print(f"  skip (exists): {dest}")
                continue
            dest.parent.mkdir(exist_ok=True)
            shutil.move(str(src), dest)
            print(f"  moved -> data/staging/{r['category']}/{src.name}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
