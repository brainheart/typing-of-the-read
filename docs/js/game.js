/* Typing of the Read — multilingual zombie typing practice.
 * Levels: 1 = unigrams, 2 = bigrams, 3 = trigrams (from corpus data files).
 */
(() => {
"use strict";

// ---------- config ----------
const KILLS_PER_LEVEL = 22;          // kills to clear a level
const LIVES = 3;
const SPAWN_Y = -16;                 // % above the top edge where zombies appear
const BITE_Y = 72;                   // % of field height where they reach the desk
const HEAT_PER_KILL = 0.012;         // every word you finish speeds the horde up a touch
const HEAT_MAX = 1.45;
// per n-gram level: descent speed (%/s) and spawn interval (ms), each [start, end-of-level]
const TUNING = {
  1: { speed: [3.0, 5.6], spawn: [2300, 1100], maxOnScreen: 6 },
  2: { speed: [2.2, 4.0], spawn: [3000, 1500], maxOnScreen: 5 },
  3: { speed: [1.7, 3.0], spawn: [3800, 1900], maxOnScreen: 4 },
};
const ZOMBIE_EMOJI = ["🧟", "🧟‍♂️", "🧟‍♀️"];
const FAST_EMOJI = "💀";
const FAST_CHANCE = 0.12;            // skeletons: faster but shorter words

// ---------- dom ----------
const $ = (id) => document.getElementById(id);
const startScreen = $("start-screen"), gameScreen = $("game-screen"), overScreen = $("over-screen");
const langSel = $("lang-select"), corpusSel = $("corpus-select"), levelSel = $("level-select");
const forgivingChk = $("forgiving"), matchCaseChk = $("matchcase");
const field = $("field"), banner = $("banner");

// ---------- state ----------
let manifest = [];
let corpus = null;                   // loaded corpus json
let pools = null;                    // weighted pools per level
let game = null;                     // live game state
let soundOn = localStorage.getItem("totr-sound") !== "off";

// ---------- normalization / matching ----------
const FINAL_HEBREW = { "ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ" };
const APOS = /['’ʼʹ`´]/;

function normChar(ch, forgiving, matchCase) {
  if (!matchCase) ch = ch.toLowerCase();
  if (ch === " " || ch === "\u00a0") return " ";
  if (APOS.test(ch)) return "'";
  if (forgiving) {
    ch = ch.normalize("NFD").replace(/\p{M}+/gu, "");
    if (ch === "") return "";                  // pure combining mark
    ch = ch.replace("\u03c2", "\u03c3").replace("\u00df", "s");
    ch = FINAL_HEBREW[ch] || ch;
  } else {
    ch = ch.replace("\u03c2", "\u03c3");                 // sigma always lenient
  }
  return ch;
}

// per displayed char, the key required to advance (forgiving collapses marks)
function buildKeys(text, forgiving, matchCase) {
  return [...text].map((c) => (c === " " ? " " : normChar(c, forgiving, matchCase)));
}

// ---------- audio (tiny webaudio synth) ----------
let actx = null;
function beep(freq, dur, type = "square", gain = 0.05) {
  if (!soundOn) return;
  try {
    actx = actx || new (window.AudioContext || window.webkitAudioContext)();
    const o = actx.createOscillator(), g = actx.createGain();
    o.type = type; o.frequency.value = freq;
    g.gain.setValueAtTime(gain, actx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.0001, actx.currentTime + dur);
    o.connect(g); g.connect(actx.destination);
    o.start(); o.stop(actx.currentTime + dur);
  } catch (e) { /* no audio available */ }
}
const sfx = {
  key:   () => beep(880, 0.04, "square", 0.025),
  kill:  () => { beep(220, 0.12, "sawtooth", 0.06); setTimeout(() => beep(110, 0.18, "sawtooth", 0.05), 60); },
  error: () => beep(140, 0.12, "square", 0.06),
  bite:  () => { beep(90, 0.3, "sawtooth", 0.09); setTimeout(() => beep(70, 0.3, "sawtooth", 0.07), 120); },
  level: () => [523, 659, 784, 1047].forEach((f, i) => setTimeout(() => beep(f, 0.12, "triangle", 0.05), i * 110)),
};

// ---------- boot: manifest & menus ----------
fetch("data/manifest.json")
  .then((r) => r.json())
  .then((m) => {
    manifest = m;
    const langs = [];
    m.forEach((c) => { if (!langs.includes(c.lang)) langs.push(c.lang); });
    langSel.innerHTML = langs
      .map((l) => `<option value="${l}">${m.find((c) => c.lang === l).langName}</option>`)
      .join("");
    langSel.value = localStorage.getItem("totr-lang") || "en";
    if (!langs.includes(langSel.value)) langSel.value = langs[0];
    fillCorpora();
  })
  .catch(() => {
    document.querySelector("#start-screen .card").insertAdjacentHTML(
      "beforeend",
      `<p style="color:#a4282a"><b>Could not load corpus data.</b>
       If you opened this file directly, serve it instead:
       <code>python3 -m http.server</code> in the docs/ folder.</p>`
    );
  });

function fillCorpora() {
  const lang = langSel.value;
  const list = manifest.filter((c) => c.lang === lang);
  corpusSel.innerHTML = list.map((c) => `<option value="${c.id}">${c.name}</option>`).join("");
  const saved = localStorage.getItem("totr-corpus");
  if (list.some((c) => c.id === saved)) corpusSel.value = saved;
  forgivingChk.checked = lang === "grc" || localStorage.getItem("totr-forgiving-" + lang) === "on";
  matchCaseChk.checked = localStorage.getItem("totr-case-" + lang) === "on";
  showHiscore();
}
langSel.addEventListener("change", fillCorpora);
corpusSel.addEventListener("change", showHiscore);
levelSel.addEventListener("change", showHiscore);

function hiKey() { return `totr-hi-${corpusSel.value}-L${levelSel.value}`; }
function showHiscore() {
  const hi = localStorage.getItem(hiKey());
  $("hiscore-line").textContent = hi ? `High score for this corpus & level: ${(+hi).toLocaleString()}` : "";
}

// ---------- corpus loading & weighted pools ----------
async function loadCorpus(id) {
  const r = await fetch(`data/${id}.json`);
  corpus = await r.json();
  // sqrt-flatten frequencies so rare-but-real n-grams still show up
  pools = corpus.levels.map((lvl) => {
    const entries = lvl.map(([text, w]) => [text, Math.sqrt(w)]);
    const total = entries.reduce((s, [, w]) => s + w, 0);
    return { entries, total };
  });
}

function pickText(level, { short } = {}) {
  const pool = pools[level - 1];
  let candidates = pool.entries;
  if (short) {
    candidates = candidates.filter(([t]) => t.length <= 6);
    if (!candidates.length) candidates = pool.entries.slice(0, 50);
  }
  const active = new Set(game.zombies.map((z) => z.text));
  const firsts = new Set(game.zombies.map((z) => z.keys[0]));
  for (let tries = 0; tries < 40; tries++) {
    const total = short ? candidates.reduce((s, [, w]) => s + w, 0) : pool.total;
    let r = Math.random() * total;
    let pickIdx = candidates.length - 1;
    for (let i = 0; i < candidates.length; i++) {
      r -= candidates[i][1];
      if (r <= 0) { pickIdx = i; break; }
    }
    const text = candidates[pickIdx][0];
    const k0 = normChar([...text][0], game.forgiving, game.matchCase);
    // avoid duplicates and first-letter clashes while options remain
    if (!active.has(text) && (!firsts.has(k0) || tries > 25)) return text;
  }
  return candidates[Math.floor(Math.random() * candidates.length)][0];
}

// ---------- game lifecycle ----------
$("start-btn").addEventListener("click", startGame);
$("retry-btn").addEventListener("click", () => { overScreen.classList.add("hidden"); startGame(); });
$("menu-btn").addEventListener("click", () => {
  overScreen.classList.add("hidden");
  startScreen.classList.remove("hidden");
  showHiscore();
});
$("sound-btn").addEventListener("click", () => {
  soundOn = !soundOn;
  $("sound-btn").textContent = soundOn ? "🔊" : "🔇";
  localStorage.setItem("totr-sound", soundOn ? "on" : "off");
});

async function startGame() {
  localStorage.setItem("totr-lang", langSel.value);
  localStorage.setItem("totr-corpus", corpusSel.value);
  localStorage.setItem("totr-forgiving-" + langSel.value, forgivingChk.checked ? "on" : "off");
  localStorage.setItem("totr-case-" + langSel.value, matchCaseChk.checked ? "on" : "off");
  await loadCorpus(corpusSel.value);

  game = {
    level: +levelSel.value,
    startLevel: +levelSel.value,
    forgiving: forgivingChk.checked,
    matchCase: matchCaseChk.checked,
    rtl: corpus.rtl,
    zombies: [],
    target: null,
    heat: 1,
    kills: 0, levelKills: 0,
    score: 0, lives: LIVES,
    keysGood: 0, keysBad: 0,
    startTime: performance.now(), activeMs: 0,
    lastSpawn: 0, lastTick: null,
    paused: false, overAt: null,
  };
  window.__totr = game;            // debug/testing handle
  field.querySelectorAll(".zombie, .splat, .score-pop").forEach((el) => el.remove());
  $("hud-corpus").textContent = corpus.name;
  $("hud-score").textContent = "0";
  updateHud();
  startScreen.classList.add("hidden");
  overScreen.classList.add("hidden");
  gameScreen.classList.remove("hidden");
  $("mobile-input").focus({ preventScroll: true });
  flashBanner(`Level ${game.level} — ${levelName(game.level)}`, corpus.name, 1400);
  requestAnimationFrame(tick);
}

function levelName(l) { return ["single words", "word pairs", "word triples"][l - 1]; }

function levelProgress() { return Math.min(game.levelKills / KILLS_PER_LEVEL, 1); }

function tuned(pair) {
  const t = levelProgress();
  return pair[0] + (pair[1] - pair[0]) * t;
}

// ---------- zombies ----------
// rotate through shuffled vertical lanes so word bubbles rarely overlap;
// fewer, wider lanes at higher levels (longer phrases)
const LANES_BY_LEVEL = {
  1: [12, 27, 42, 57, 72, 87],
  2: [16, 39, 62, 85],
  3: [22, 50, 78],
};
let laneOrder = [], laneIdx = 0;
function nextLane() {
  const lanes = LANES_BY_LEVEL[game.level];
  if (laneIdx >= laneOrder.length || laneOrder.length !== lanes.length) {
    laneOrder = [...lanes].sort(() => Math.random() - 0.5);
    laneIdx = 0;
  }
  return laneOrder[laneIdx++] + (Math.random() * 4 - 2);
}

function spawnZombie() {
  const cfg = TUNING[game.level];
  const fast = game.level === 1 && Math.random() < FAST_CHANCE;
  const text = pickText(game.level, { short: fast });
  const z = {
    text,
    chars: [...text],
    keys: buildKeys(text, game.forgiving, game.matchCase),
    pos: 0,
    x: nextLane(),                                    // % of field width
    y: SPAWN_Y,
    speed: tuned(cfg.speed) * (fast ? 1.9 : 0.92 + Math.random() * 0.25),
    el: document.createElement("div"),
    dead: false,
  };
  z.el.className = "zombie" + (fast ? " fast" : "");
  z.el.innerHTML =
    `<span class="word" dir="${game.rtl ? "rtl" : "ltr"}"></span>` +
    `<span class="body">${fast ? FAST_EMOJI : ZOMBIE_EMOJI[Math.floor(Math.random() * ZOMBIE_EMOJI.length)]}</span>`;
  z.el.style.top = z.y + "%";
  z.el.style.left = z.x + "%";
  renderWord(z);
  field.appendChild(z.el);
  // keep long word bubbles inside the field (zombie is centered on x)
  const halfPct = (z.el.offsetWidth / 2 / field.offsetWidth) * 100;
  z.x = Math.min(Math.max(z.x, halfPct + 1), 99 - halfPct);
  z.el.style.left = z.x + "%";
  game.zombies.push(z);
}

function renderWord(z) {
  const done = z.chars.slice(0, z.pos).join("");
  const due = z.chars.slice(z.pos).join("");
  z.el.querySelector(".word").innerHTML =
    `<span class="done">${esc(done)}</span><span class="due">${esc(due)}</span>`;
}
function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/ /g, "&nbsp;");
}

function killZombie(z) {
  z.dead = true;
  if (game.target === z) game.target = null;
  z.el.classList.add("dying");
  const splat = document.createElement("span");
  splat.className = "splat";
  splat.textContent = "🖋️💥";
  splat.style.left = z.x + "%"; splat.style.top = (z.y + 6) + "%";
  field.appendChild(splat);
  setTimeout(() => splat.remove(), 1000);

  const pts = z.chars.length * 10 * game.level;
  game.score += pts;
  const pop = document.createElement("span");
  pop.className = "score-pop";
  pop.textContent = "+" + pts;
  pop.style.left = z.x + "%"; pop.style.top = z.y + "%";
  field.appendChild(pop);
  setTimeout(() => pop.remove(), 900);

  setTimeout(() => z.el.remove(), 600);
  game.zombies = game.zombies.filter((other) => other !== z);
  game.kills++; game.levelKills++;
  game.heat = Math.min(game.heat + HEAT_PER_KILL, HEAT_MAX);
  sfx.kill();
  updateHud();

  if (game.levelKills >= KILLS_PER_LEVEL) advanceLevel();
}

function biteDesk(z) {
  z.dead = true;
  if (game.target === z) game.target = null;
  z.el.remove();
  game.zombies = game.zombies.filter((other) => other !== z);
  game.lives--;
  sfx.bite();
  const desk = $("desk");
  desk.classList.remove("bitten"); void desk.offsetWidth; desk.classList.add("bitten");
  updateHud();
  if (game.lives <= 0) endGame(false);
}

function advanceLevel() {
  if (game.level < 3) {
    game.level++;
    game.levelKills = 0;
    sfx.level();
    flashBanner(`Level ${game.level} — ${levelName(game.level)}`, "the dead grow wordier…", 1600);
  } else {
    endGame(true);
  }
  updateHud();
}

// ---------- loop ----------
function tick(now) {
  if (!game || game.overAt) return;
  if (game.lastTick == null) game.lastTick = now;
  const dt = Math.min((now - game.lastTick) / 1000, 0.1);
  game.lastTick = now;

  if (!game.paused) {
    game.activeMs += dt * 1000;
    const cfg = TUNING[game.level];
    if (now - game.lastSpawn > tuned(cfg.spawn) && game.zombies.length < cfg.maxOnScreen) {
      game.lastSpawn = now;
      spawnZombie();
    }
    for (const z of [...game.zombies]) {
      if (z.dead) continue;
      z.y += z.speed * game.heat * dt;
      z.el.style.top = z.y + "%";
      if (z.y >= BITE_Y) biteDesk(z);
    }
  }
  requestAnimationFrame(tick);
}

// ---------- typing ----------
window.addEventListener("keydown", (e) => {
  if (!game || gameScreen.classList.contains("hidden")) return;
  if (e.key === "Escape") { togglePause(); return; }
  if (game.paused || game.overAt) return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key.length !== 1) return;
  e.preventDefault();
  handleKey(e.key);
});

// mobile: route hidden-input characters into the game
$("mobile-input").addEventListener("input", (e) => {
  const v = e.target.value;
  if (v && game && !game.paused && !game.overAt) handleKey(v[v.length - 1]);
  e.target.value = "";
});
field.addEventListener("pointerdown", () => $("mobile-input").focus({ preventScroll: true }));

function handleKey(rawKey) {
  const key = normChar(rawKey, game.forgiving, game.matchCase);
  if (key === "") return;

  let z = game.target;
  if (z && (z.dead || z.keys[z.pos] !== key)) {
    if (!z.dead) { miss(); return; }       // locked target: wrong key
    z = null;
  }
  if (!z) {
    // closest-to-desk (lowest) zombie whose next key matches
    const candidates = game.zombies.filter((c) => !c.dead && c.keys[c.pos] === key);
    if (!candidates.length) { miss(); return; }
    candidates.sort((a, b) => b.y - a.y);
    z = candidates[0];
    game.target = z;
    z.el.classList.add("target");
  }

  z.pos++;
  game.keysGood++;
  sfx.key();
  renderWord(z);
  if (z.pos >= z.chars.length) killZombie(z);
}

function miss() {
  game.keysBad++;
  sfx.error();
  field.classList.remove("error"); void field.offsetWidth; field.classList.add("error");
}

// ---------- pause / banners / hud ----------
function togglePause() {
  game.paused = !game.paused;
  if (game.paused) showBanner("⏸ Paused", "press Esc to resume");
  else hideBanner();
}
window.addEventListener("blur", () => {
  if (game && !game.overAt && !gameScreen.classList.contains("hidden") && !game.paused) togglePause();
});

let bannerTimer = null;
function showBanner(text, sub) {
  banner.innerHTML = esc2(text) + (sub ? `<small>${esc2(sub)}</small>` : "");
  banner.classList.remove("hidden");
}
function flashBanner(text, sub, ms) {
  clearTimeout(bannerTimer);
  showBanner(text, sub);
  bannerTimer = setTimeout(hideBanner, ms);
}
function hideBanner() { banner.classList.add("hidden"); }
function esc2(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;"); }

function updateHud() {
  $("hud-level").textContent = `Lv ${game.level}/3`;
  $("hud-score").textContent = game.score.toLocaleString();
  $("hud-lives").textContent = "❤️".repeat(Math.max(game.lives, 0)) + "🖤".repeat(LIVES - Math.max(game.lives, 0));
  $("progress-bar").style.width = (levelProgress() * 100) + "%";
}

// ---------- end ----------
function endGame(won) {
  game.overAt = performance.now();
  hideBanner();
  const minutes = game.activeMs / 60000;
  const wpm = minutes > 0 ? Math.round(game.keysGood / 5 / minutes) : 0;
  const total = game.keysGood + game.keysBad;
  const acc = total ? Math.round((game.keysGood / total) * 100) : 100;

  const prev = +(localStorage.getItem(hiKey()) || 0);
  const best = game.score > prev;
  if (best) localStorage.setItem(hiKey(), game.score);

  $("over-title").textContent = won
    ? "🏆 The Library Stands!"
    : "📚 The Library Has Fallen";
  $("over-stats").innerHTML =
    `<div>${esc2(corpus.name)} — started at level ${game.startLevel}</div>` +
    `<div>Zombies stopped: <b>${game.kills}</b></div>` +
    `<div>Score: <b>${game.score.toLocaleString()}</b>${best ? ' <span class="newbest">★ new best!</span>' : ""}</div>` +
    `<div>Speed: <b>${wpm}</b> WPM &nbsp;·&nbsp; Accuracy: <b>${acc}%</b></div>`;
  setTimeout(() => {
    gameScreen.classList.add("hidden");
    overScreen.classList.remove("hidden");
  }, won ? 600 : 900);
}

})();
