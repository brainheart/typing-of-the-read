# Typing of the Read 🧟📖

A multilingual zombie typing game in the spirit of *The Typing of the Dead*:
zombies shamble toward your library desk, each carrying a word or phrase from
great literature — type it to stop them. Practice your typing **and** your
languages at the same time.

**Play locally:**

```bash
cd docs && python3 -m http.server 8000
# open http://localhost:8000
```

## Languages & corpora

| Language | Corpora |
|---|---|
| English | Shakespeare, King James Bible, Melville, Alice in Wonderland |
| German | Luther Bible, Grimms Märchen |
| Hebrew | Tanakh, Pirkei Avot + Mishnah Berakhot |
| Ancient Greek | Homer (Iliad & Odyssey), Greek New Testament (SBLGNT) |
| Italian | Dante (Divine Comedy), Pinocchio |
| Latin | Virgil (Aeneid), Caesar (De Bello Gallico) |
| French | Voltaire (Candide), Jules Verne (20 000 lieues) |
| Spanish | Cervantes (Don Quijote), Bécquer (Obras escogidas) |

The contabulate-derived corpora reuse the n-gram token data from the
[contabulate.org](https://contabulate.org) instances; the "general" corpora
are built from public-domain texts (Project Gutenberg, SBLGNT, Sefaria).

## Levels

1. **Single words** (unigrams)
2. **Word pairs** (bigrams — type the space too)
3. **Word triples** (trigrams)

Clear 22 zombies to advance. Word choice is frequency-weighted (√-flattened),
so you mostly practice the vocabulary that matters most in that corpus.

## Features

- **Forgiving keys** mode: accent/diacritic-insensitive matching (on by
  default for polytonic Ancient Greek; also folds Hebrew final letters and ß).
- Hebrew renders right-to-left; you type in normal (logical) letter order.
- First keystroke locks a target, like the original arcade game.
- WPM, accuracy, score, per-corpus/level high scores (localStorage).
- Tiny WebAudio sound effects (mutable), no dependencies, fully static.

## Deploying to GitHub Pages

The site lives entirely in `docs/`. Create a GitHub repo, push, then enable
**Settings → Pages → Deploy from branch → `main` / `docs/`**.

## Rebuilding corpus data

```bash
python3 scripts/build_corpus.py            # all corpora
python3 scripts/build_corpus.py kjv homer  # just some
```

Sources are read from `sources/` (downloaded texts and remote contabulate
token files) and from local `~/proj/contabulates/*/docs/data` where present.
Output goes to `docs/data/*.json` plus a `manifest.json`.

`sources/` is not committed; to recreate it:

- Remote contabulate token data: `https://{homer,dante,aeneid}.contabulate.org/data/tokens{,2,3}.json`
  into `sources/<site>/`.
- Gutenberg texts into `sources/texts/` (via `https://www.gutenberg.org/cache/epub/<id>/pg<id>.txt`):
  alice=11, quijote=2000, candide=4650, verne=5097, grimm=77905,
  pinocchio=52484, caesar=18837, cuentos=53552.
- `gnt.txt`: SBLGNT verse text from <https://github.com/LogosBible/SBLGNT>
  (strip the `Book C:V<tab>` prefixes).
- `avot.txt`: Pirkei Avot 1–6 + Mishnah Berakhot 1–9 via the Sefaria API
  (`https://www.sefaria.org/api/texts/...`), HTML tags stripped.
