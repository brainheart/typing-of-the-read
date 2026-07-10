#!/usr/bin/env python3
"""Build game corpus files for Typing of the Read.

Every corpus is a hand-curated plain-text file in curated/:
one word or phrase per line, and the word count decides the level
(1 word = level 1 ... 5 words = level 5). Blank lines and # comments
are ignored; duplicates and 6+-word lines are skipped with a warning.

Output: docs/data/<id>.json  {id, name, lang, rtl, levels: [L1..L5]}
plus docs/data/manifest.json describing all corpora.

Usage:
    python3 scripts/build_corpus.py              # build everything
    python3 scripts/build_corpus.py genz-en kjv  # just some
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data"
CURATED = ROOT / "curated"

# apostrophe-like characters normalized to U+2019 for display consistency
APOS = "'’ʼʹ`´"

# Hebrew niqqud + cantillation range to strip
HEBREW_MARKS = re.compile(r"[֑-ׇ]")

LANG_NAMES = {
    "en": "English", "de": "German", "fr": "French", "es": "Spanish",
    "it": "Italian", "la": "Latin", "grc": "Ancient Greek", "he": "Hebrew",
}

# id -> (display name, lang, rtl); the phrase file is curated/<id>.txt
CORPORA = {
    # literary
    "shakespeare": ("Shakespeare", "en", False),
    "kjv": ("King James Bible", "en", False),
    "melville": ("Herman Melville", "en", False),
    "austen": ("Jane Austen", "en", False),
    "alice": ("Alice in Wonderland", "en", False),
    "luther": ("Luther Bible", "de", False),
    "grimm": ("Grimms Märchen", "de", False),
    "tanakh": ("Tanakh — Hebrew Bible", "he", True),
    "avot": ("Pirkei Avot", "he", True),
    "homer": ("Homer — Iliad & Odyssey", "grc", False),
    "gnt": ("Greek New Testament", "grc", False),
    "dante": ("Dante — Divine Comedy", "it", False),
    "pinocchio": ("Pinocchio", "it", False),
    "aeneid": ("Virgil — Aeneid", "la", False),
    "caesar": ("Caesar — De Bello Gallico", "la", False),
    "candide": ("Voltaire — Candide", "fr", False),
    "verne": ("Jules Verne — 20.000 lieues", "fr", False),
    "quijote": ("Cervantes — Don Quijote", "es", False),
    "cuentos": ("Bécquer — Rimas y Leyendas", "es", False),
    # novelty
    "aiisms-en": ("AI-isms", "en", False),
    "genz-en": ("Gen Z memes", "en", False),
    "constitution-en": ("Claude’s Constitution", "en", False),
    "aiisms-de": ("KI-Floskeln", "de", False),
    "genz-de": ("Jugendsprache", "de", False),
    "amtsdeutsch-de": ("Amtsdeutsch", "de", False),
    "aiisms-fr": ("Tics de l’IA", "fr", False),
    "genz-fr": ("Argot des jeunes", "fr", False),
    "dissertation-fr": ("Style de dissertation", "fr", False),
    "aiisms-es": ("Muletillas de la IA", "es", False),
    "genz-es": ("Jerga juvenil", "es", False),
    "aiisms-it": ("Frasi fatte dell’IA", "it", False),
    "genz-it": ("Slang giovanile", "it", False),
    "aiisms-la": ("Formulae scholasticae", "la", False),
    "genz-la": ("Sermo iuvenum", "la", False),
    "aiisms-grc": ("Λόγοι τῶν φιλοσόφων", "grc", False),
    "genz-grc": ("Γλῶττα τῶν νέων", "grc", False),
    "aiisms-he": ("קלישאות בינה מלאכותית", "he", True),
    "genz-he": ("סלנג ישראלי", "he", True),
}

# corpus order within each language's dropdown: literary first, then novelty,
# preserved by the insertion order above


def normalize_token(text, lang):
    text = unicodedata.normalize("NFC", text)
    for a in APOS:
        text = text.replace(a, "’")
    if lang == "he":
        text = HEBREW_MARKS.sub("", text)
        text = text.replace("־", " ")  # maqaf splits words
    return text


def from_phrases(path, lang):
    levels = [[] for _ in range(5)]
    seen = set()
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        phrase = re.sub(r"\s+", " ", normalize_token(line, lang))
        if phrase in seen:
            print(f"  warn {path.name}:{lineno}: duplicate {phrase!r} skipped")
            continue
        seen.add(phrase)
        n = len(phrase.split(" "))
        if n > 5:
            print(f"  warn {path.name}:{lineno}: {n} words (max 5), skipped: {phrase!r}")
            continue
        levels[n - 1].append([phrase, 10])
    return levels


def main():
    only = set(sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for cid, (name, lang, rtl) in CORPORA.items():
        entry = {"id": cid, "name": name, "lang": lang,
                 "langName": LANG_NAMES[lang], "rtl": rtl}
        manifest.append(entry)
        if only and cid not in only:
            continue
        levels = from_phrases(CURATED / f"{cid}.txt", lang)
        out = dict(entry, levels=levels)
        (OUT / f"{cid}.json").write_text(
            json.dumps(out, ensure_ascii=False, separators=(",", ":")))
        print(f"built {cid}: {[len(l) for l in levels]}")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"manifest: {len(manifest)} corpora")


if __name__ == "__main__":
    main()
