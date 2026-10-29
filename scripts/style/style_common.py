"""
Shared helpers for the AgentBrain style tools (check_style, local_humanizer, learn_style):
LaTeX -> prose, sentence splitting, metrics, and the author profile.

The profile lives at $AGENTBRAIN_PATH/style/author_profile.yaml (default ~/.agentbrain).
Dependency-free: PyYAML is used when present, JSON (valid YAML) otherwise.
"""

import json
import os
import re
import statistics
from pathlib import Path

# Generic AI filler. The profile's `forbidden_phrases` extends this list.
DEFAULT_FORBIDDEN = [
    # Croatian
    "ključno je napomenuti", "važno je napomenuti", "valja napomenuti", "valja istaknuti",
    "potrebno je naglasiti", "treba naglasiti", "u današnje vrijeme", "u današnjem svijetu",
    "u današnjem dinamičnom", "sveobuhvatna analiza", "sveobuhvatnu analizu", "sveobuhvatan pregled",
    "igra ključnu ulogu", "igraju ključnu ulogu", "od iznimne je važnosti", "neizostavan dio",
    "neizostavni dio", "u konačnici", "nema sumnje da", "bez sumnje", "revolucionaran",
    "u svijetu koji se brzo mijenja",
    # English
    "delve into", "delves into", "crucial to note", "it is important to note", "it is worth noting",
    "in today's world", "in today's fast-paced", "comprehensive analysis", "plays a crucial role",
    "plays a pivotal role", "a testament to", "in the realm of", "navigate the complexities",
    "ever-evolving", "seamlessly", "unlock the potential",
]

# Safe, deterministic rewrites used by local_humanizer. "" deletes a lead-in phrase
# (skipped when a Croatian clitic follows: "da je X" cannot simply lose its "da").
DEFAULT_REPLACEMENTS = {
    "ključno je napomenuti da ": "",
    "važno je napomenuti da ": "",
    "valja napomenuti da ": "",
    "valja istaknuti da ": "",
    "potrebno je naglasiti da ": "",
    "treba naglasiti da ": "",
    "nema sumnje da ": "",
    "u današnje vrijeme, ": "danas ",
    "u današnje vrijeme ": "danas ",
    "u današnjem svijetu, ": "danas ",
    "u današnjem svijetu ": "danas ",
    "sveobuhvatna analiza": "analiza",
    "sveobuhvatnu analizu": "analizu",
    "sveobuhvatan pregled": "pregled",
    "u konačnici, ": "",
    "it is important to note that ": "",
    "it is worth noting that ": "",
    "it is crucial to note that ": "",
    "in today's world, ": "today ",
    "delve into": "examine",
    "delves into": "examines",
    "comprehensive analysis": "analysis",
    "plays a crucial role in": "strongly affects",
    "plays a pivotal role in": "strongly affects",
}

DEFAULT_TARGETS = {
    "min_score": 75,
    "min_burstiness": 0.45,     # stdev/mean of sentence length (words)
    "short_sentence_words": 8,
    "long_sentence_words": 40,
}

# Environments whose content is not prose.
_SKIP_ENVS = ("equation", "equation*", "align", "align*", "gather", "gather*", "multline",
              "figure", "figure*", "table", "table*", "tabular", "tikzpicture", "lstlisting",
              "minted", "verbatim", "thebibliography")
_DROP_WITH_ARG = ("cite", "citep", "citet", "ref", "eqref", "autoref", "cref", "label", "url",
                  "includegraphics", "input", "include", "bibliography", "bibliographystyle",
                  "section", "section*", "subsection", "subsection*", "subsubsection",
                  "subsubsection*", "chapter", "chapter*", "paragraph", "caption", "footnote")
_ABBREVIATIONS = ("npr", "tj", "sl", "str", "dr", "sc", "prof", "itd", "god", "br", "sv", "tzv",
                  "odn", "usp", "npr", "e.g", "i.e", "etc", "fig", "eq", "vs", "al", "cf", "approx")

# Croatian enclitics: a sentence cannot start with them, so deleting "…da " before one
# would leave broken word order ("Je sustav razvijen").
CLITICS = {"je", "su", "se", "sam", "si", "smo", "ste", "će", "ću", "ćemo", "ćete", "bi", "bismo",
           "biste", "ga", "mu", "joj", "ih", "im", "me", "mi", "te", "ti", "nas", "vas", "li"}

_UPPER = "A-ZČĆŠĐŽ"
_WORD_RE = re.compile(r"[A-Za-zČĆŠĐŽčćšđž0-9][\wČĆŠĐŽčćšđž'-]*")
# Croatian periphrastic passive: a form of "biti" followed by a passive participle.
_PASSIVE_RE = re.compile(
    r"\b(je|su|bio|bila|bilo|bili|bile|biti|će biti|bit će|jest)\s+(\w+\s+)?"
    r"\w+(an|en|ena|eno|eni|ene|ana|ano|ani|ane|ovan|ovana|ovano|ovani|ljen|ljena|ljeno|ljeni|"
    r"nut|nuta|nuto|nuti|jen|jena|jeno|jeni)\b"
    r"|\b(is|are|was|were|been|being|be)\s+(\w+ly\s+)?\w+(ed|en)\b",
    re.IGNORECASE,
)


def brain_dir():
    return Path(os.environ.get("AGENTBRAIN_PATH") or (Path.home() / ".agentbrain")).expanduser()


def profile_path(override=None):
    return Path(override) if override else brain_dir() / "style" / "author_profile.yaml"


def load_profile(path=None):
    """Profile dict with defaults applied; missing file -> defaults only."""
    p = profile_path(path)
    data = {}
    if p.exists():
        text = p.read_text(encoding="utf-8")
        try:
            import yaml
            data = yaml.safe_load(text) or {}
        except ImportError:
            data = json.loads(text)
    targets = {**DEFAULT_TARGETS, **(data.get("targets") or {})}
    forbidden = list(dict.fromkeys(DEFAULT_FORBIDDEN + list(data.get("forbidden_phrases") or [])))
    replacements = {**DEFAULT_REPLACEMENTS, **(data.get("replacements") or {})}
    return {**data, "targets": targets, "forbidden_phrases": forbidden, "replacements": replacements}


def save_profile(data, path=None):
    p = profile_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml
        text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
    except ImportError:
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    p.write_text(text, encoding="utf-8")
    return p


def tex_to_prose(text):
    """Strip LaTeX markup, keeping the running text of paragraphs."""
    text = re.sub(r"(?<!\\)%.*", "", text)                                   # comments
    for env in _SKIP_ENVS:
        e = re.escape(env)
        text = re.sub(rf"\\begin\{{{e}\}}.*?\\end\{{{e}\}}", " ", text, flags=re.S)
    text = re.sub(r"\\\[.*?\\\]", " X ", text, flags=re.S)                  # display math
    text = re.sub(r"\$\$.*?\$\$", " X ", text, flags=re.S)
    text = re.sub(r"(?<!\\)\$.*?(?<!\\)\$", " X ", text, flags=re.S)       # inline math
    drop = "|".join(re.escape(c) for c in _DROP_WITH_ARG)
    text = re.sub(rf"\\({drop})(\[[^\]]*\])*\{{[^{{}}]*\}}", " ", text)
    text = re.sub(r"\\(begin|end)\{[^}]*\}", " ", text)
    text = re.sub(r"\\[A-Za-z]+\*?(\[[^\]]*\])?\{([^{}]*)\}", r"\2", text)  # \emph{x} -> x
    text = re.sub(r"\\[A-Za-z]+\*?(\[[^\]]*\])?", " ", text)                # bare commands
    text = text.replace("~", " ").replace("\\\\", " ")
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\s+\.", ".", text)
    return re.sub(r"[ \t]+", " ", text)


def split_sentences(prose):
    """Sentences of the prose, abbreviation-aware (Croatian + English)."""
    protected = prose
    for abbr in _ABBREVIATIONS:
        protected = re.sub(rf"\b({re.escape(abbr)})\.", r"\1<DOT>", protected, flags=re.I)
    protected = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", protected)
    parts = re.split(rf"(?<=[.!?])\s+(?=[\"„“(]?[{_UPPER}0-9])", protected)
    sentences = []
    for part in parts:
        s = " ".join(part.replace("<DOT>", ".").split())
        if words(s):
            sentences.append(s)
    return sentences


def words(sentence):
    return _WORD_RE.findall(sentence)


def find_phrases(text, phrases):
    """[(phrase, line_no)] for each case-insensitive occurrence in the raw text."""
    hits = []
    for no, line in enumerate(text.splitlines(), 1):
        low = re.sub(r"(?<!\\)%.*", "", line).lower()   # ignore LaTeX comments
        for ph in phrases:
            if ph.lower() in low:
                hits.append((ph, no))
    return hits


def metrics(sentences, targets=None):
    targets = targets or DEFAULT_TARGETS
    lengths = [len(words(s)) for s in sentences]
    if not lengths:
        return {"sentences": 0}
    mean = statistics.mean(lengths)
    stdev = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    openers = [words(s)[0].lower() for s in sentences if words(s)]
    repeats = sum(1 for i in range(2, len(openers)) if openers[i] == openers[i - 1] == openers[i - 2])
    return {
        "sentences": len(lengths),
        "words": sum(lengths),
        "mean_sentence_words": round(mean, 1),
        "stdev_sentence_words": round(stdev, 1),
        "burstiness": round(stdev / mean, 2) if mean else 0.0,
        "short_share": round(sum(n <= targets["short_sentence_words"] for n in lengths) / len(lengths), 2),
        "long_share": round(sum(n > targets["long_sentence_words"] for n in lengths) / len(lengths), 2),
        "passive_share": round(sum(bool(_PASSIVE_RE.search(s)) for s in sentences) / len(sentences), 2),
        "repeated_openers": repeats,
    }
