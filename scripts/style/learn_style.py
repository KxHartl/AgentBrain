"""
AgentBrain learn_style — build the author profile from your own writing.

Measures sentence rhythm, passive share, typical sentence openers and frequent
content words in texts you wrote yourself, and stores them under `learned:` in
~/.agentbrain/style/author_profile.yaml. check_style compares new chapters against
it; the writer agent reads it (and style/samples/) to match your voice.

Usage (via the project helper):
    style.sh learn docs/chapters/01-uvod.tex [more files ...] [--save-sample]
--save-sample also copies the files into ~/.agentbrain/style/samples/.

Only feed it text YOU wrote: learning from AI drafts teaches the profile the voice
it is meant to filter out.

Rebuilt 2026-09 from the contract in the LiteRealm style helper and the writer agent;
the original was lost with the work disk (see RECOVERY.md).
"""

import argparse
import collections
import datetime as dt
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from style_common import (brain_dir, metrics, profile_path, save_profile,  # noqa: E402
                          split_sentences, tex_to_prose, words)

STOPWORDS = set("""
i a u na je se da za od do s sa o ili što koji koja koje kojeg kojem kojim su biti bio bila bilo
bili će ne to ta te taj ovaj ova ovo ovi kao po pri iz prema kod te li ako već samo još tako
the of and to in a is for on that with as by it be are this an or from at which can not
""".split())


def learn(texts):
    sentences = []
    for text, is_tex in texts:
        sentences.extend(split_sentences(tex_to_prose(text) if is_tex else text))
    m = metrics(sentences)
    openers = collections.Counter(words(s)[0].lower() for s in sentences if words(s))
    vocab = collections.Counter(w.lower() for s in sentences for w in words(s)
                                if len(w) > 3 and w.lower() not in STOPWORDS and not w.isdigit())
    return {
        **{k: m[k] for k in ("sentences", "words", "mean_sentence_words", "stdev_sentence_words",
                             "burstiness", "short_share", "long_share", "passive_share") if k in m},
        "common_openers": [w for w, _ in openers.most_common(10)],
        "frequent_terms": [w for w, _ in vocab.most_common(30)],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Learn the author's style profile.")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--profile", help="author profile path")
    parser.add_argument("--save-sample", action="store_true", help="copy files into style/samples/")
    args = parser.parse_args(argv)

    texts = []
    for f in args.files:
        p = Path(f)
        if not p.is_file():
            print(f"Not found: {f}", file=sys.stderr)
            return 2
        texts.append((p.read_text(encoding="utf-8", errors="replace"), p.suffix == ".tex"))

    learned = learn(texts)
    if not learned.get("sentences"):
        print("No prose found - nothing learned.", file=sys.stderr)
        return 1

    # Merge into what the user wrote in the profile (defaults are applied at load time only).
    path = profile_path(args.profile)
    profile = _raw_profile(path) if path.exists() else {}
    learned["updated"] = dt.date.today().isoformat()
    learned["sources"] = sorted(set((profile.get("learned") or {}).get("sources", []) + [Path(f).name for f in args.files]))
    profile["learned"] = learned
    save_profile(profile, args.profile)

    if args.save_sample:
        samples = brain_dir() / "style" / "samples"
        samples.mkdir(parents=True, exist_ok=True)
        for f in args.files:
            shutil.copy2(f, samples / Path(f).name)
        print(f"Copied {len(args.files)} sample(s) to {samples}")

    print(f"Profile updated: {path}")
    print(f"  {learned['sentences']} sentences, mean {learned['mean_sentence_words']} words, "
          f"burstiness {learned['burstiness']}, passive {int(learned['passive_share'] * 100)} %")
    print(f"  openers: {', '.join(learned['common_openers'][:5])}")
    return 0


def _raw_profile(path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        import json
        return json.loads(text)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
