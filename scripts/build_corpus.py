#!/usr/bin/env python3
"""Build compact game corpus files (top n-grams with weights) for Typing of the Read.

Two source types:
  - contabulate: a directory containing tokens.json / tokens2.json / tokens3.json
    (token -> [[chunk_id, count], ...])
  - text: one or more plain-text files, tokenized here into 1/2/3-grams.

Output: docs/data/<id>.json  {id, name, lang, rtl, levels: [1..5-grams]}
        each level is a list of [text, weight] sorted by weight desc.
Also writes docs/data/manifest.json describing all corpora.
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data"
SRC = ROOT / "sources"
CONTAB = Path.home() / "proj" / "contabulates"

TOP_N = 500
MIN_UNIGRAM_LEN = 2

# apostrophe-like characters normalized to U+2019 for display consistency
APOS = "'’ʼʹ`´"

# Hebrew niqqud + cantillation range to strip
HEBREW_MARKS = re.compile(r"[֑-ׇ]")

WORD_RE = re.compile(
    r"[^\W\d_]+(?:[" + APOS + r"\-][^\W\d_]+)*[" + APOS + r"]?",
    re.UNICODE,
)

BAD_TOKEN = re.compile(r"\d")


def normalize_token(tok, lang):
    tok = unicodedata.normalize("NFC", tok)
    for a in APOS:
        tok = tok.replace(a, "’")
    if lang == "he":
        tok = HEBREW_MARKS.sub("", tok)
        tok = tok.replace("־", " ")  # maqaf -> split later
    return tok


def ok_token(tok, n):
    if BAD_TOKEN.search(tok):
        return False
    words = tok.split(" ")
    if len(words) != n:
        return False
    if n == 1 and len(tok.rstrip("’")) < MIN_UNIGRAM_LEN:
        return False
    # every word must contain at least one letter
    return all(any(unicodedata.category(c).startswith("L") for c in w) for w in words)


def tokenize_text(text, lang):
    """Tokenize, preserving original case (the game offers case-sensitive play)."""
    text = unicodedata.normalize("NFC", text)
    if lang == "he":
        text = HEBREW_MARKS.sub("", text)
        text = text.replace("\u05be", " ")
    return [normalize_token(m.group(0), lang) for m in WORD_RE.finditer(text)]


def ngram_levels(sentences, lang):
    """Count n-grams case-insensitively; display the most common cased form."""
    toks = []
    sentinel = ""
    for sent in sentences:
        toks.extend(tokenize_text(sent, lang))
        toks.append(sentinel)
    levels = []
    for n in (1, 2, 3, 4, 5):
        counts = Counter()
        surfaces = {}
        for i in range(len(toks) - n + 1):
            gram = toks[i : i + n]
            if sentinel in gram:
                continue
            surface = " ".join(gram)
            key = surface.lower()
            if not ok_token(key, n):
                continue
            counts[key] += 1
            surfaces.setdefault(key, Counter())[surface] += 1
        levels.append(
            [(surfaces[k].most_common(1)[0][0], c) for k, c in counts.most_common(TOP_N)]
        )
    return levels


def from_lines(path, lang):
    rows = json.loads(Path(path).read_text())
    sentences = []
    for row in rows:
        # a line is a sentence boundary; also split on sentence punctuation
        sentences.extend(re.split(r"[.!?;:·;׃]+", row.get("text", "")))
    return ngram_levels(sentences, lang)


def from_text(paths, lang):
    sentences = []
    for p in paths:
        text = strip_gutenberg(Path(p).read_text(encoding="utf-8", errors="replace"))
        sentences.extend(re.split(r"[.!?;:·;׃\n]+", text))
    return ngram_levels(sentences, lang)


def strip_gutenberg(text):
    m = re.search(r"\*\*\* ?START OF.*?\*\*\*", text)
    if m:
        text = text[m.end():]
    m = re.search(r"\*\*\* ?END OF", text)
    if m:
        text = text[: m.start()]
    return text


CORPORA = [
    # id, name, lang, rtl, source type, source
    ("shakespeare", "Shakespeare — Complete Works", "en", False, "lines", CONTAB / "shakespeare-contabulate/docs/lines/all_lines.json"),
    ("kjv", "King James Bible", "en", False, "lines", CONTAB / "kjv-contabulate/docs/lines/all_lines.json"),
    ("melville", "Herman Melville", "en", False, "lines", CONTAB / "melville-contabulate/docs/lines/all_lines.json"),
    ("alice", "Alice in Wonderland (general)", "en", False, "text", ["alice.txt"]),
    ("luther", "Luther Bible", "de", False, "lines", CONTAB / "luther-contabulate/docs/lines/all_lines.json"),
    ("grimm", "Grimms Märchen (general)", "de", False, "text", ["grimm.txt"]),
    ("tanakh", "Tanakh — Hebrew Bible", "he", True, "lines", CONTAB / "tanakh-contabulate/docs/lines/all_lines.json"),
    ("avot", "Pirkei Avot (general)", "he", True, "text", ["avot.txt"]),
    ("homer", "Homer — Iliad & Odyssey", "grc", False, "lines", SRC / "homer/all_lines.json"),
    ("gnt", "Greek New Testament (general)", "grc", False, "text", ["gnt.txt"]),
    ("dante", "Dante — Divine Comedy", "it", False, "lines", SRC / "dante/all_lines.json"),
    ("pinocchio", "Pinocchio (general)", "it", False, "text", ["pinocchio.txt"]),
    ("aeneid", "Virgil — Aeneid", "la", False, "lines", SRC / "aeneid/all_lines.json"),
    ("caesar", "Caesar — De Bello Gallico (general)", "la", False, "text", ["caesar.txt"]),
    ("candide", "Voltaire — Candide", "fr", False, "text", ["candide.txt"]),
    ("verne", "Jules Verne — 20.000 lieues (general)", "fr", False, "text", ["verne.txt"]),
    ("quijote", "Cervantes — Don Quijote", "es", False, "text", ["quijote.txt"]),
    ("cuentos", "Bécquer — Obras escogidas (general)", "es", False, "text", ["cuentos.txt"]),
]

CURATED = ROOT / "curated"
# curated phrase corpora: hand-written, exact word counts per level.
# labels are native to each language
AIISMS_NAMES = {
    "en": "AI-isms",
    "de": "KI-Floskeln",
    "fr": "Tics de l\u2019IA",
    "es": "Muletillas de la IA",
    "it": "Frasi fatte dell\u2019IA",
    "la": "Formulae machinae loquentis",
    "grc": "\u039b\u03cc\u03b3\u03bf\u03b9 \u03c4\u1fc6\u03c2 \u03bc\u03b7\u03c7\u03b1\u03bd\u1fc6\u03c2",
    "he": "\u05e7\u05dc\u05d9\u05e9\u05d0\u05d5\u05ea \u05d1\u05d9\u05e0\u05d4 \u05de\u05dc\u05d0\u05db\u05d5\u05ea\u05d9\u05ea",
}
GENZ_NAMES = {
    "en": "Gen Z memes",
    "de": "Jugendsprache",
    "fr": "Argot des jeunes",
    "es": "Jerga juvenil",
    "it": "Slang giovanile",
    "la": "Sermo iuvenum",
    "grc": "\u0393\u03bb\u1ff6\u03c4\u03c4\u03b1 \u03c4\u1ff6\u03bd \u03bd\u03ad\u03c9\u03bd",
    "he": "\u05e1\u05dc\u05e0\u05d2 \u05d9\u05e9\u05e8\u05d0\u05dc\u05d9",
}
for _lang in ["en", "de", "fr", "es", "it", "la", "grc", "he"]:
    CORPORA.append((f"aiisms-{_lang}", AIISMS_NAMES[_lang], _lang, _lang == "he", "curated", (CURATED / "aiisms.json", _lang)))
    CORPORA.append((f"genz-{_lang}", GENZ_NAMES[_lang], _lang, _lang == "he", "curated", (CURATED / "genz.json", _lang)))


def from_curated(source, lang):
    path, key = source
    data = json.loads(Path(path).read_text())[key]
    levels = []
    for n in ("1", "2", "3", "4", "5"):
        lst = data.get(n, [])
        # descending weights: earlier entries are the most iconic
        levels.append([[normalize_token(t, lang), len(lst) - i + 4] for i, t in enumerate(lst)])
    return levels


LANG_NAMES = {
    "en": "English", "de": "German", "fr": "French", "es": "Spanish",
    "it": "Italian", "la": "Latin", "grc": "Ancient Greek", "he": "Hebrew",
}

def main():
    only = set(sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for cid, name, lang, rtl, kind, source in CORPORA:
        outfile = OUT / f"{cid}.json"
        entry = {"id": cid, "name": name, "lang": lang,
                 "langName": LANG_NAMES[lang], "rtl": rtl}
        if only and cid not in only:
            if outfile.exists():
                manifest.append(entry)
            continue
        try:
            if kind == "lines":
                levels = from_lines(source, lang)
            elif kind == "curated":
                levels = from_curated(source, lang)
            else:
                paths = [SRC / "texts" / f for f in source]
                if not all(p.exists() for p in paths):
                    print(f"skip {cid}: missing {[str(p) for p in paths if not p.exists()]}")
                    continue
                levels = from_text(paths, lang)
        except FileNotFoundError as e:
            print(f"skip {cid}: {e}")
            continue
        out = dict(entry)
        out["levels"] = levels
        outfile.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
        sizes = [len(l) for l in levels]
        print(f"built {cid}: {sizes} ngrams, {outfile.stat().st_size//1024} KB")
        manifest.append(entry)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"manifest: {len(manifest)} corpora")


if __name__ == "__main__":
    main()
