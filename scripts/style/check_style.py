"""
AgentBrain style linter — Human Style Score (0-100) for LaTeX/Markdown/plain text.

Penalises generic AI filler phrases, monotonous sentence rhythm (low burstiness),
too many very long sentences, heavy passive chains and repeated sentence openers,
and (when learn_style has built one) drift from the author's own profile.

Usage (via the project helper):
    style.sh check docs/chapters/01-uvod.tex [more.tex ...] [--threshold 75] [--json]
Exit code 1 when any file scores below the threshold (default: profile min_score, 75).

Rebuilt 2026-09 from the contract in the qa_reviewer agent ("Human Style Score > 75");
the original was lost with the work disk (see RECOVERY.md).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from style_common import find_phrases, load_profile, metrics, split_sentences, tex_to_prose  # noqa: E402


def score(m, cliche_hits, profile):
    """(score, [issues]) from the metrics of one document."""
    t = profile["targets"]
    issues, penalty = [], 0.0
    if m.get("sentences", 0) == 0:
        return 0, ["no prose found"]

    p = min(40, 5 * len(cliche_hits))
    if p:
        issues.append(f"{len(cliche_hits)} AI filler phrase(s) (-{p})")
    penalty += p

    if m["sentences"] >= 5 and m["burstiness"] < t["min_burstiness"]:
        p = min(25, round((t["min_burstiness"] - m["burstiness"]) * 60))
        issues.append(f"monotonous rhythm: burstiness {m['burstiness']} < {t['min_burstiness']} (-{p})")
        penalty += p
    if m["sentences"] >= 8 and m["short_share"] < 0.1:
        issues.append(f"almost no short sentences (<= {t['short_sentence_words']} words) (-8)")
        penalty += 8
    if m["long_share"] > 0.15:
        p = min(15, round(m["long_share"] * 40))
        issues.append(f"{int(m['long_share'] * 100)} % sentences over {t['long_sentence_words']} words (-{p})")
        penalty += p
    if m["passive_share"] > 0.4:
        p = min(15, round((m["passive_share"] - 0.4) * 50))
        issues.append(f"passive voice in {int(m['passive_share'] * 100)} % of sentences (-{p})")
        penalty += p
    if m["repeated_openers"]:
        p = min(10, 3 * m["repeated_openers"])
        issues.append(f"{m['repeated_openers']} run(s) of 3 sentences with the same opener (-{p})")
        penalty += p

    learned = profile.get("learned") or {}
    ref = learned.get("mean_sentence_words")
    if ref and abs(m["mean_sentence_words"] - ref) / ref > 0.4:
        issues.append(f"mean sentence length {m['mean_sentence_words']} vs your {ref} (-8)")
        penalty += 8
    return max(0, round(100 - penalty)), issues


def check_file(path, profile):
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    prose = tex_to_prose(raw) if str(path).endswith(".tex") else raw
    sentences = split_sentences(prose)
    m = metrics(sentences, profile["targets"])
    hits = find_phrases(raw, profile["forbidden_phrases"])
    s, issues = score(m, hits, profile)
    return {"file": str(path), "score": s, "metrics": m, "issues": issues,
            "cliches": [{"phrase": ph, "line": ln} for ph, ln in hits]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Human Style Score linter.")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--threshold", type=int, help="minimum passing score (default: profile min_score)")
    parser.add_argument("--profile", help="author profile path (default: ~/.agentbrain/style/author_profile.yaml)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    profile = load_profile(args.profile)
    threshold = args.threshold if args.threshold is not None else profile["targets"]["min_score"]
    results = []
    for f in args.files:
        if not Path(f).is_file():
            print(f"Not found: {f}", file=sys.stderr)
            return 2
        results.append(check_file(f, profile))

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            verdict = "PASS" if r["score"] >= threshold else "FAIL"
            m = r["metrics"]
            print(f"{r['file']}: Human Style Score {r['score']}/100  [{verdict}, threshold {threshold}]")
            if m.get("sentences"):
                print(f"  {m['sentences']} sentences, mean {m['mean_sentence_words']} words, "
                      f"burstiness {m['burstiness']}, passive {int(m['passive_share'] * 100)} %")
            for issue in r["issues"]:
                print(f"  - {issue}")
            for c in r["cliches"]:
                print(f"    line {c['line']}: \"{c['phrase']}\"")
    return 1 if any(r["score"] < threshold for r in results) else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
