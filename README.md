# Typing of the Read 🧟📖

A multilingual zombie typing game in the spirit of *The Typing of the Dead*:
zombies descend from the stacks above toward your library desk, each carrying
a word or phrase from great literature — type it to stop them. Practice your
typing **and** your languages at the same time.

**Play locally:**

```bash
cd docs && python3 -m http.server 8000
# open http://localhost:8000
```

## Languages & corpora

| Language | Corpora |
|---|---|
| English | Shakespeare, King James Bible, Melville, Jane Austen, Alice in Wonderland |
| German | Luther Bible, Grimms Märchen |
| Hebrew | Tanakh, Pirkei Avot |
| Ancient Greek | Homer (Iliad & Odyssey), Greek New Testament |
| Italian | Dante (Divine Comedy), Pinocchio |
| Latin | Virgil (Aeneid), Caesar (De Bello Gallico) |
| French | Voltaire (Candide), Jules Verne (20 000 lieues) |
| Spanish | Cervantes (Don Quijote), Bécquer (Rimas y Leyendas) |

Every language additionally has hand-curated novelty corpora, with native
labels that match their actual register:
chatbot clichés where they really are chatbot clichés (**AI-isms**,
**Muletillas de la IA**, **Frasi fatte dell'IA**, **קלישאות בינה מלאכותית**),
blends labeled as blends (**KI-Floskeln & Amtsdeutsch**, **Tics de l'IA &
de dissertation**), and scholastic/philosophical formulas for the ancient
tongues (**Formulae scholasticae**, **Λόγοι τῶν φιλοσόφων**); plus youth
slang (**Gen Z memes**, **Jugendsprache**, **Argot des jeunes**, **Jerga
juvenil**, **Slang giovanile**, **Sermo iuvenum**, **Γλῶττα τῶν νέων**,
**סלנג ישראלי**).

Every corpus — literary and novelty alike — is a hand-curated list of its
most recognizable, distinctive, wow words and phrases: *out damned spot*,
*Rumpelstilzchen*, *ῥοδοδάκτυλος Ἠώς*, *molinos de viento*, *il faut
cultiver notre jardin*. (Earlier versions generated the literary lists by
n-gram frequency from the full texts; curation won.)

## Levels

1. **Single words** (unigrams)
2. **Word pairs** (bigrams — type the space too)
3. **Word triples** (trigrams)
4. **Four-word phrases** (4-grams)
5. **Five-word phrases** (5-grams — `And it came to pass`…)

Clear 15 zombies to advance.

## Features

- Corpora keep original case (`spricht der HERR`, `dijo don Quijote`): words
  display the most common cased form found in the text. Matching ignores case
  by default; turn on **Match case** to require capitals — good German practice.
- **Forgiving keys** mode, on by default: type plain letters for accents,
  umlauts and diacritics (ä→a, ß→s, polytonic Greek, Hebrew final letters).
  Turn it off for strict practice.
- Hebrew renders right-to-left; you type in normal (logical) letter order.
- First keystroke locks a target, like the original arcade game; Tab cycles
  the lock to another zombie (handy when the target is still off-screen).
- Successful keystrokes clack like an old typewriter — every strike slightly
  different, space bar thunks deeper, and a carriage bell rings per kill.
- Every word you finish makes the horde descend a touch faster (caps at +45%).
- **Challenge links**: `?lang=de&corpus=luther&level=3` (plus optional
  `&case=1` and `&strict=1`) auto-starts that exact setup — use the
  "Copy challenge link" button on the start screen, or just copy the address
  bar mid-game. Great for sending a friend a duel.
- A recently-shown memory keeps phrases from repeating until a good chunk of
  the pool has cycled through.
- WPM, accuracy, score, per-corpus/level high scores (localStorage).
- Procedural WebAudio sound (toggle with 🔊): zombies gurgle out a wet groan
  when slain and squelch-chomp-gulp when they reach the desk — males groan
  low, females higher, skeletons rattle dryly. No audio files, no
  dependencies, fully static.

## Deploying to GitHub Pages

The site lives entirely in `docs/`. Create a GitHub repo, push, then enable
**Settings → Pages → Deploy from branch → `main` / `docs/`**.

## Editing the word lists

Every corpus is a plain text file in `curated/` (e.g. `curated/shakespeare.txt`,
`curated/genz-en.txt`): **one word or phrase per line**, and the number of
words decides the level (1 word = level 1 … 5 words = level 5; 6+ words are
skipped with a warning). Blank lines and `#` comments are ignored, duplicates
are reported, order doesn't matter. Add lines as inspiration strikes, then:

```bash
python3 scripts/build_corpus.py shakespeare   # rebuild just that corpus
python3 scripts/build_corpus.py               # or everything
```

then commit and push — GitHub Pages redeploys automatically.
