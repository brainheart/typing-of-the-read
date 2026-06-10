#!/usr/bin/env python3
"""Build compact game corpus files (top n-grams with weights) for Typing of the Read.

Two source types:
  - contabulate: a directory containing tokens.json / tokens2.json / tokens3.json
    (token -> [[chunk_id, count], ...])
  - text: one or more plain-text files, tokenized here into 1/2/3-grams.

Output: docs/data/<id>.json  {id, name, lang, rtl, levels: [unigrams, bigrams, trigrams]}
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


def from_contabulate(dirpath, lang):
    levels = []
    for n, fname in enumerate(["tokens.json", "tokens2.json", "tokens3.json"], 1):
        data = json.loads((Path(dirpath) / fname).read_text())
        counts = Counter()
        for tok, occ in data.items():
            tok = normalize_token(tok, lang)
            tok = re.sub(r"\s+", " ", tok).strip()
            if ok_token(tok, n):
                counts[tok] += sum(c for _, c in occ)
        levels.append(counts.most_common(TOP_N))
    return levels


def tokenize_text(text, lang):
    text = unicodedata.normalize("NFC", text)
    if lang == "he":
        text = HEBREW_MARKS.sub("", text)
        text = text.replace("־", " ")
    toks = []
    for m in WORD_RE.finditer(text):
        tok = normalize_token(m.group(0), lang)
        # lowercase only for cased scripts (German nouns lose caps, matching
        # the contabulate convention of lowercased tokens)
        toks.append(tok.lower())
    return toks


def from_text(paths, lang):
    toks = []
    sentinel = ""
    for p in paths:
        text = Path(p).read_text(encoding="utf-8", errors="replace")
        text = strip_gutenberg(text)
        # don't let n-grams span sentence boundaries
        for sent in re.split(r"[.!?;:·;׃\n]{1,}", text):
            toks.extend(tokenize_text(sent, lang))
            toks.append(sentinel)
    levels = []
    for n in (1, 2, 3):
        counts = Counter()
        for i in range(len(toks) - n + 1):
            gram = toks[i : i + n]
            if sentinel in gram:
                continue
            tok = " ".join(gram)
            if ok_token(tok, n):
                counts[tok] += 1
        levels.append(counts.most_common(TOP_N))
    return levels


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
    ("shakespeare", "Shakespeare — Complete Works", "en", False, "contab", CONTAB / "shakespeare-contabulate/docs/data"),
    ("kjv", "King James Bible", "en", False, "contab", CONTAB / "kjv-contabulate/docs/data"),
    ("melville", "Herman Melville", "en", False, "contab", CONTAB / "melville-contabulate/docs/data"),
    ("alice", "Alice in Wonderland (general)", "en", False, "text", ["alice.txt"]),
    ("luther", "Luther Bible", "de", False, "contab", CONTAB / "luther-contabulate/docs/data"),
    ("grimm", "Grimms Märchen (general)", "de", False, "text", ["grimm.txt"]),
    ("tanakh", "Tanakh — Hebrew Bible", "he", True, "contab", SRC / "tanakh"),
    ("avot", "Pirkei Avot (general)", "he", True, "text", ["avot.txt"]),
    ("homer", "Homer — Iliad & Odyssey", "grc", False, "contab", SRC / "homer"),
    ("gnt", "Greek New Testament (general)", "grc", False, "text", ["gnt.txt"]),
    ("dante", "Dante — Divine Comedy", "it", False, "contab", SRC / "dante"),
    ("pinocchio", "Pinocchio (general)", "it", False, "text", ["pinocchio.txt"]),
    ("aeneid", "Virgil — Aeneid", "la", False, "contab", SRC / "aeneid"),
    ("caesar", "Caesar — De Bello Gallico (general)", "la", False, "text", ["caesar.txt"]),
    ("candide", "Voltaire — Candide", "fr", False, "text", ["candide.txt"]),
    ("verne", "Jules Verne — 20.000 lieues (general)", "fr", False, "text", ["verne.txt"]),
    ("quijote", "Cervantes — Don Quijote", "es", False, "text", ["quijote.txt"]),
    ("cuentos", "Bécquer — Obras escogidas (general)", "es", False, "text", ["cuentos.txt"]),
]

LANG_NAMES = {
    "en": "English", "de": "German", "fr": "French", "es": "Spanish",
    "it": "Italian", "la": "Latin", "grc": "Ancient Greek", "he": "Hebrew",
}

# tanakh data also lives locally; prefer local copy
TANAKH_LOCAL = CONTAB / "tanakh-contabulate/docs/data"


def main():
    only = set(sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for cid, name, lang, rtl, kind, source in CORPORA:
        if cid == "tanakh" and TANAKH_LOCAL.exists():
            source = TANAKH_LOCAL
        outfile = OUT / f"{cid}.json"
        entry = {"id": cid, "name": name, "lang": lang,
                 "langName": LANG_NAMES[lang], "rtl": rtl}
        if only and cid not in only:
            if outfile.exists():
                manifest.append(entry)
            continue
        try:
            if kind == "contab":
                levels = from_contabulate(source, lang)
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
