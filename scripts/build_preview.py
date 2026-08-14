#!/usr/bin/env python3
"""Build the Felix's Notes interface from the indexed community data.

Each note is a short piece of text plus its links — that is the whole record.
This renders them as a single self-contained page.

Writes two files:
  index.html          complete standalone document, for hosting
  preview/index.html  bare fragment, for the Artifact preview
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "notes_index.json"
DOCS = ROOT / "data" / "raw" / "docs"
OUT = ROOT / "index.html"
FRAGMENT = ROOT / "preview" / "index.html"

LINK_LABELS = {
    "source_doc": "Open the note",
    "watchlist_sheet": "Watchlist",
    "article": "Read the note",
    "heartbeat": "Heartbeat Scanner",
    "video": "Watch the video",
}

MD_NOISE = re.compile(r"[#*_`\[\]()>]|https?://\S+")


def recap(text: str, limit: int = 150) -> str:
    """A short plain-text recap for the cards."""
    flat = MD_NOISE.sub(" ", text or "")
    flat = re.sub(r"\s+", " ", flat).strip()
    if len(flat) <= limit:
        return flat
    return flat[:limit].rsplit(" ", 1)[0] + "…"


def collect() -> dict:
    index = json.loads(INDEX.read_text())
    notes = []

    for note in index["notes"]:
        if note.get("kind") != "weekly_note":
            continue

        body = None
        for doc_id in note.get("doc_ids", []):
            path = DOCS / f"{doc_id}.md"
            if path.exists() and path.read_text().strip():
                body = path.read_text().strip()
                break
        if body is None and note.get("source_type") == "inline":
            body = note.get("post_text") or None

        links = []
        for url in note.get("doc_urls", []):
            links.append({"kind": "source_doc", "url": url})
        for sheet_id in note.get("sheet_ids", []):
            links.append({
                "kind": "watchlist_sheet",
                "url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
            })
        for url in note.get("article_urls", []):
            links.append({"kind": "article", "url": url})
        for url in note.get("heartbeat_urls", []):
            links.append({"kind": "heartbeat", "url": url})
        for url in note.get("video_urls", []):
            links.append({"kind": "video", "url": url})

        text = note.get("post_text") or ""
        notes.append({
            "id": note["post_id"],
            "title": note["title"],
            "date": note.get("note_date"),
            "author": note.get("author") or "Felix Prehn",
            "postUrl": note.get("post_url"),
            "text": text,
            "body": body,
            "recap": recap(body or text),
            "links": links,
        })

    notes.sort(key=lambda n: (n["date"] or "0000-00-00"), reverse=True)
    years = sorted({n["date"][:4] for n in notes if n["date"]}, reverse=True)
    return {"notes": notes, "years": years, "linkLabels": LINK_LABELS}


PAGE = r"""<title>Felix's Notes Archive</title>
<style>
/* ── tokens ─────────────────────────────────────────────────────────────── */
/* Light theme is tinted toward the brand teal rather than plain white, so
   borders and panels actually read as structure. */
:root {
  --bg: #eef5f9;
  --panel: #ffffff;
  --panel-2: #e7f1f7;
  --line: #b6d5e5;
  --line-soft: #d3e6ef;
  --ink: #0c1c24;
  --ink-2: #3b5964;
  --ink-3: #5e7f8c;

  --brand: #0f6ba6;
  --brand-2: #12809c;
  --green: #17914c;
  --gold: #a8720c;
  --mark: #ade5f5;
  --shadow: 0 1px 3px rgba(12, 28, 36, .08);

  /* One clean sans throughout — the serif was harder on the eye at length. */
  --ui: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #080a0b;
    --panel: #121517;
    --panel-2: #181f23;
    --line: #2a353b;
    --line-soft: #1f272b;
    --ink: #f2f6f8;
    --ink-2: #a8b4bb;
    --ink-3: #7b8b93;

    --brand: #2fa8e0;
    --brand-2: #35b1e8;
    --green: #3ddc84;
    --gold: #e0b44c;
    --mark: #12455c;
    --shadow: 0 1px 3px rgba(0, 0, 0, .45);
  }
}
:root[data-theme="dark"] {
  --bg: #080a0b;
  --panel: #121517;
  --panel-2: #181f23;
  --line: #2a353b;
  --line-soft: #1f272b;
  --ink: #f2f6f8;
  --ink-2: #a8b4bb;
  --ink-3: #7b8b93;

  --brand: #2fa8e0;
  --brand-2: #35b1e8;
  --green: #3ddc84;
  --gold: #e0b44c;
  --mark: #12455c;
  --shadow: 0 1px 3px rgba(0, 0, 0, .45);
}

* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: var(--ui); font-size: 16px; line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 62rem; margin: 0 auto; padding: 0 1.5rem; }
button { font: inherit; cursor: pointer; }

/* ── banner ─────────────────────────────────────────────────────────────── */
.banner {
  background: linear-gradient(115deg,#0b5f5c 0%,#0f6f92 48%,#1b93cf 100%);
  color: #fff;
}
.banner-in { display: flex; align-items: center; gap: 1.35rem; padding: 2.9rem 0 3rem; }
.mark {
  flex: none; width: 74px; height: 74px; border-radius: 19px; display: grid;
  place-items: center; background: rgba(255,255,255,.15);
  border: 1px solid rgba(255,255,255,.3);
}
.mark svg { width: 38px; height: 38px; }
.banner h1 {
  margin: 0; font-size: clamp(1.9rem, 4.6vw, 3.05rem); font-weight: 800;
  line-height: 1.02; letter-spacing: -.02em; text-transform: uppercase;
  text-wrap: balance;
}
.banner .sub { margin: .5rem 0 0; font-size: 1.02rem; color: rgba(255,255,255,.85); }
.banner-acts { margin-left: auto; display: flex; align-items: center; gap: .6rem; }
.gbtn {
  display: inline-flex; align-items: center; gap: .45rem; padding: .55rem 1rem;
  border-radius: 999px; background: rgba(255,255,255,.14); color: #fff;
  border: 1px solid rgba(255,255,255,.32); font-size: .84rem; font-weight: 700;
}
.gbtn:hover { background: rgba(255,255,255,.26); }
.gbtn[aria-pressed="true"] { background: #fff; color: #0f6f92; border-color: #fff; }
.gbtn svg { width: 17px; height: 17px; }
.gicon { padding: .55rem; width: 42px; height: 42px; justify-content: center; }

/* ── sections ───────────────────────────────────────────────────────────── */
.sec { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; margin: 2rem 0 .9rem; }
.sec h2 { margin: 0; font-size: 1.15rem; font-weight: 800; letter-spacing: -.01em; }
.sec p { margin: 0; font-size: .86rem; color: var(--ink-3); }

/* ── latest cards ───────────────────────────────────────────────────────── */
.rail { display: flex; gap: .9rem; overflow-x: auto; scroll-snap-type: x mandatory; padding: .2rem .2rem 1rem; margin: 0 -.2rem; }
.rail::-webkit-scrollbar { height: 8px; }
.rail::-webkit-scrollbar-thumb { background: var(--line); border-radius: 99px; }
.card {
  flex: 0 0 17.5rem; scroll-snap-align: start; text-align: left;
  padding: 1.1rem 1.2rem; border-radius: 14px; background: var(--panel);
  border: 1px solid var(--line); box-shadow: var(--shadow); color: inherit;
  transition: transform .14s ease, border-color .14s ease;
}
.card:hover { transform: translateY(-3px); border-color: var(--brand-2); }
.card .when { font-size: .72rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--brand-2); }
.card h3 { margin: .5rem 0 .45rem; font-size: 1.03rem; font-weight: 750; line-height: 1.3; letter-spacing: -.01em; }
.card p { margin: 0; font-size: .89rem; line-height: 1.52; color: var(--ink-2);
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }

/* ── filters ────────────────────────────────────────────────────────────── */
.filters { display: flex; flex-wrap: wrap; gap: .6rem; margin-bottom: 1rem; }
.searchbox { position: relative; flex: 1 1 18rem; }
.searchbox svg { position: absolute; left: .85rem; top: 50%; transform: translateY(-50%); width: 17px; height: 17px; color: var(--ink-3); }
#q, #year {
  padding: .68rem .9rem; border-radius: 10px; background: var(--panel);
  border: 1px solid var(--line); color: var(--ink); font-size: .93rem;
}
#q { width: 100%; padding-left: 2.4rem; }
#q:focus, #year:focus { outline: 2px solid var(--brand-2); outline-offset: -1px; }
.selwrap { position: relative; }
#year { appearance: none; padding-right: 2.4rem; font-weight: 650; cursor: pointer; }
.selwrap::after {
  content: ""; position: absolute; right: 1rem; top: 50%; width: 8px; height: 8px;
  margin-top: -6px; border-right: 2px solid var(--ink-3); border-bottom: 2px solid var(--ink-3);
  transform: rotate(45deg); pointer-events: none;
}

/* ── list ───────────────────────────────────────────────────────────────── */
.list { border: 1px solid var(--line); border-radius: 14px; overflow: hidden; background: var(--panel); }
.ygroup { display: flex; align-items: baseline; gap: .7rem; padding: .75rem 1.2rem; background: var(--panel-2); border-bottom: 1px solid var(--line); }
.ygroup b { font-size: 1.3rem; font-weight: 800; letter-spacing: -.02em; }
.ygroup span { font-size: .74rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: var(--ink-3); }
.row { display: flex; align-items: center; gap: .3rem; padding-left: .5rem; border-bottom: 1px solid var(--line-soft); }
.row:last-child { border-bottom: 0; }
.row:hover { background: var(--panel-2); }

/* A checkbox, because it is the control that marks a note read — a bare icon
   here gave no clue what it did. */
.readbox { flex: none; width: 44px; height: 44px; display: grid; place-items: center; background: none; border: 0; padding: 0; }
.box { width: 20px; height: 20px; border-radius: 6px; border: 2px solid var(--line); display: grid; place-items: center; background: var(--panel); }
.box svg { width: 12px; height: 12px; color: #fff; opacity: 0; }
.readbox:hover .box { border-color: var(--green); }
.is-read .box { background: var(--green); border-color: var(--green); }
.is-read .box svg { opacity: 1; }

.open { flex: 1; min-width: 0; display: flex; align-items: center; gap: .9rem; padding: .8rem .3rem; background: none; border: 0; color: inherit; text-align: left; }
.d { flex: none; width: 6.6rem; font-size: .83rem; font-weight: 700; color: var(--ink-3); font-variant-numeric: tabular-nums; }
.t { flex: 1; min-width: 0; font-size: .98rem; font-weight: 700; letter-spacing: -.005em; }
.is-read .t { font-weight: 500; color: var(--ink-2); }
.ctx { display: block; margin-top: .18rem; font-size: .85rem; font-weight: 400; line-height: 1.45; color: var(--ink-3); }

.save {
  flex: none; margin-right: .9rem; display: inline-flex; align-items: center; gap: .35rem;
  padding: .36rem .72rem; border-radius: 8px; background: var(--panel-2);
  border: 1px solid var(--line); color: var(--ink-2); font-size: .78rem; font-weight: 700;
}
.save svg { width: 14px; height: 14px; }
.save:hover { border-color: var(--gold); color: var(--gold); }
.save[aria-pressed="true"] { color: var(--gold); border-color: var(--gold); background: transparent; }
.save[aria-pressed="true"] svg { fill: currentColor; }

.empty { padding: 3.2rem 1.5rem; text-align: center; color: var(--ink-3); }
.empty b { display: block; margin-bottom: .3rem; color: var(--ink); font-size: 1.05rem; }

/* ── dialog ─────────────────────────────────────────────────────────────── */
dialog {
  width: min(44rem, 94vw); max-height: 88vh; padding: 0; border: 1px solid var(--line);
  border-radius: 18px; background: var(--panel); color: var(--ink);
  box-shadow: 0 24px 60px rgba(0,0,0,.28);
}
dialog::backdrop { background: rgba(6,16,22,.6); }
.sheet { display: flex; flex-direction: column; max-height: 88vh; }
.sheet-h { display: flex; gap: 1rem; align-items: flex-start; padding: 1.4rem 1.6rem 1.1rem; border-bottom: 1px solid var(--line); }
.sheet-h .when { font-size: .72rem; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; color: var(--brand-2); }
.sheet-h h2 { margin: .3rem 0 .3rem; font-size: 1.45rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.2; }
.sheet-h p { margin: 0; font-size: .83rem; color: var(--ink-3); }
.x { flex: none; width: 38px; height: 38px; border-radius: 9px; background: var(--panel-2); border: 1px solid var(--line); color: var(--ink-2); display: grid; place-items: center; }
.x svg { width: 17px; height: 17px; }
.x:hover { color: var(--brand-2); border-color: var(--brand-2); }
.sheet-b { padding: 1.3rem 1.6rem 1.7rem; overflow-y: auto; }
.prose {
  font-size: 1.06rem; line-height: 1.78; letter-spacing: .002em;
  white-space: pre-wrap; overflow-wrap: break-word; margin: 0 0 1.4rem;
  color: var(--ink);
}
.prose a { color: var(--brand-2); font-weight: 600; overflow-wrap: anywhere; }
.mynote { padding: 1rem 1.15rem; border-radius: 12px; background: var(--panel-2); border: 1px solid var(--line); }
.mynote h4 { margin: 0 0 .55rem; font-size: .69rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: var(--ink-3); }
.mynote textarea {
  width: 100%; min-height: 5.5rem; resize: vertical; padding: .7rem .85rem;
  border-radius: 9px; border: 1px solid var(--line); background: var(--panel);
  color: var(--ink); font: inherit; font-size: .95rem; line-height: 1.6;
}
.mynote textarea:focus { outline: 2px solid var(--brand-2); outline-offset: -1px; }
.mynote .saved-tick { margin: .4rem 0 0; font-size: .76rem; font-weight: 650; color: var(--green); opacity: 0; transition: opacity .2s; }
.mynote .saved-tick.on { opacity: 1; }
mark { background: var(--mark); color: inherit; border-radius: 3px; padding: 0 .12em; }

footer { margin-top: 2.5rem; padding: 1.5rem 0 2.5rem; border-top: 1px solid var(--line); color: var(--ink-3); font-size: .82rem; }
footer p { margin: 0; }
:focus-visible { outline: 2px solid var(--brand-2); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
@media (max-width: 44rem) {
  .banner-in { flex-wrap: wrap; padding: 2rem 0 2.2rem; gap: 1rem; }
  .banner-acts { margin-left: 0; width: 100%; }
  .d { width: 100%; }
  .open { flex-wrap: wrap; gap: .2rem .8rem; }
}
</style>

<header class="banner">
  <div class="wrap banner-in">
    <div class="mark" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 2h8l5 5v15a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"/>
        <path d="M14 2v5h5"/><path d="M9 13h6M9 17h6M9 9h2"/>
      </svg>
    </div>
    <div>
      <h1>Felix&rsquo;s Market Notes</h1>
      <p class="sub">Every weekly note, in one place</p>
    </div>
    <div class="banner-acts">
      <button class="gbtn" id="bmfilter" aria-pressed="false">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/></svg>
        <span id="bmlabel">Bookmarked</span>
      </button>
      <button class="gbtn gicon" id="theme" aria-label="Switch theme"></button>
    </div>
  </div>
</header>

<div class="wrap">
  <div class="sec">
    <h2>Latest notes</h2>
    <p>The five most recent</p>
  </div>
  <div class="rail" id="rail"></div>

  <div class="sec">
    <h2>All notes</h2>
    <p id="shown"></p>
  </div>

  <div class="filters">
    <div class="searchbox">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
      <input id="q" type="search" placeholder="Search notes&hellip;" aria-label="Search notes" autocomplete="off">
    </div>
    <div class="selwrap"><select id="year" aria-label="Filter by year"></select></div>
  </div>

  <div class="list" id="list"></div>

  <footer>
    <p>Historical market commentary, archived for reference. Not financial advice.</p>
  </footer>
</div>

<dialog id="sheet"><div class="sheet">
  <div class="sheet-h">
    <div style="flex:1;min-width:0">
      <span class="when" id="s-when"></span>
      <h2 id="s-title"></h2>
      <p id="s-by"></p>
    </div>
    <div style="display:flex;gap:.5rem;flex:none">
      <button class="save" id="s-save" aria-pressed="false" style="margin:0" title="Save this note"></button>
      <button class="x" id="s-close" aria-label="Close">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
      </button>
    </div>
  </div>
  <div class="sheet-b">
    <div id="s-text"></div>
    <div class="mynote">
      <h4>My note</h4>
      <textarea id="s-mynote" placeholder="Why is this one worth remembering?"></textarea>
      <p class="saved-tick" id="s-tick">Saved</p>
    </div>
  </div>
</div></dialog>

<script>
const DATA = __DATA__;
const NOTES = DATA.notes;
const KEY = "felix-notes-v2";

const ICON = {
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.5l5.5 5.5L20 6"/></svg>',
  bookmark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 13A9 9 0 1 1 11 3a7 7 0 0 0 10 10z"/></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>',
};

let state = { read: [], bm: [], theme: null, mine: {} };
try { Object.assign(state, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
const read = new Set(state.read || []);
const bm = new Set(state.bm || []);
const mine = state.mine && typeof state.mine === "object" ? state.mine : {};
const save = () => {
  try {
    localStorage.setItem(KEY, JSON.stringify(
      { read: [...read], bm: [...bm], theme: state.theme, mine }));
  } catch (e) {}
};

let onlyBm = false;
let year = "all";
let query = "";

/* ── theme ──────────────────────────────────────────────────────────────── */
const themeBtn = document.getElementById("theme");
const isDark = () => state.theme
  ? state.theme === "dark"
  : matchMedia("(prefers-color-scheme: dark)").matches;

function paintTheme() {
  if (state.theme) document.documentElement.setAttribute("data-theme", state.theme);
  else document.documentElement.removeAttribute("data-theme");
  themeBtn.innerHTML = isDark() ? ICON.sun : ICON.moon;
}
themeBtn.addEventListener("click", () => {
  state.theme = isDark() ? "light" : "dark";
  paintTheme(); save();
});
paintTheme();

/* ── helpers ────────────────────────────────────────────────────────────── */
const esc = s => (s ?? "").replace(/[&<>"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

const fmt = d => d ? new Date(d + "T00:00:00Z").toLocaleDateString("en-GB",
  { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }) : "Undated";
const fmtLong = d => d ? new Date(d + "T00:00:00Z").toLocaleDateString("en-GB",
  { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }) : "Undated";

function hl(text, q) {
  if (!q) return esc(text);
  const re = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig");
  return esc(text).replace(re, "<mark>$1</mark>");
}

/* The note text carries its links inline as plain URLs, so turn them into
   real links rather than listing them separately. */
function linkify(text) {
  return esc(text).replace(/https?:\/\/[^\s<]+/g, raw => {
    const url = raw.replace(/[.,;:)\]]+$/, "");
    const tail = raw.slice(url.length);
    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>${tail}`;
  });
}

/* When a note matches on its text rather than its title, show the passage that
   matched — otherwise the row gives no clue why it is in the results. */
function matchLine(n, q) {
  if (!q || n.title.toLowerCase().includes(q.toLowerCase())) return "";
  const hay = n.body || n.text || "";
  const at = hay.toLowerCase().indexOf(q.toLowerCase());
  if (at < 0) return "";
  const from = Math.max(0, at - 55);
  const raw = (from ? "…" : "") + hay.slice(from, at + q.length + 85).replace(/\s+/g, " ").trim() + "…";
  return `<span class="ctx">${hl(raw, q)}</span>`;
}

const matches = n => {
  if (year !== "all" && (n.date || "").slice(0, 4) !== year) return false;
  if (onlyBm && !bm.has(n.id)) return false;
  if (!query) return true;
  const q = query.toLowerCase();
  return n.title.toLowerCase().includes(q)
    || (n.body || "").toLowerCase().includes(q)
    || n.text.toLowerCase().includes(q);
};

/* ── latest cards ───────────────────────────────────────────────────────── */
function renderRail() {
  document.getElementById("rail").innerHTML = NOTES.slice(0, 5).map(n => `
    <button class="card" data-id="${esc(n.id)}">
      <span class="when">${fmt(n.date)}</span>
      <h3>${esc(n.title)}</h3>
      <p>${esc(n.recap)}</p>
    </button>`).join("");
}

/* ── year dropdown ──────────────────────────────────────────────────────── */
/* A dropdown rather than buttons: a new year arrives every January and a
   growing row would eventually wrap across the page. */
function renderYears() {
  const opts = [["all", `All years (${NOTES.length})`]].concat(
    DATA.years.map(y => [y,
      `${y} (${NOTES.filter(n => (n.date || "").slice(0, 4) === y).length})`]));
  document.getElementById("year").innerHTML = opts.map(([v, label]) =>
    `<option value="${v}"${year === v ? " selected" : ""}>${label}</option>`).join("");
}

/* ── list ───────────────────────────────────────────────────────────────── */
function renderList() {
  const hits = NOTES.filter(matches);
  const el = document.getElementById("list");
  document.getElementById("shown").textContent =
    hits.length === NOTES.length ? `${NOTES.length} notes`
                                 : `${hits.length} of ${NOTES.length} notes`;

  if (!hits.length) {
    el.innerHTML = `<div class="empty"><b>Nothing to show</b>${
      onlyBm ? "Save a note and it will appear here." : "Try a different search or year."}</div>`;
    return;
  }

  const groups = new Map();
  for (const n of hits) {
    const y = n.date ? n.date.slice(0, 4) : "Undated";
    if (!groups.has(y)) groups.set(y, []);
    groups.get(y).push(n);
  }

  el.innerHTML = [...groups].map(([y, rows]) => `
    <div class="ygroup"><b>${y}</b><span>${rows.length} note${rows.length === 1 ? "" : "s"}</span></div>
    ${rows.map(n => `
      <div class="row ${read.has(n.id) ? "is-read" : ""}">
        <button class="readbox" data-read="${esc(n.id)}" role="checkbox"
          aria-checked="${read.has(n.id)}"
          title="${read.has(n.id) ? "Mark as unread" : "Mark as read"}">
          <span class="box">${ICON.check}</span></button>
        <button class="open" data-id="${esc(n.id)}">
          <span class="d">${fmt(n.date)}</span>
          <span class="t">${hl(n.title, query)}${matchLine(n, query)}</span>
        </button>
        <button class="save" data-bm="${esc(n.id)}" aria-pressed="${bm.has(n.id)}"
          title="Save this note">${ICON.bookmark}${bm.has(n.id) ? "Saved" : "Save"}</button>
      </div>`).join("")}`).join("");
}

/* ── detail ─────────────────────────────────────────────────────────────── */
const sheet = document.getElementById("sheet");

let openId = null;

function paintSheetSave() {
  const btn = document.getElementById("s-save");
  btn.innerHTML = ICON.bookmark + (bm.has(openId) ? "Saved" : "Save");
  btn.setAttribute("aria-pressed", bm.has(openId));
}

function openNote(id) {
  const n = NOTES.find(x => x.id === id);
  if (!n) return;
  openId = id;

  document.getElementById("s-when").textContent = fmtLong(n.date);
  document.getElementById("s-title").textContent = n.title;
  document.getElementById("s-by").textContent = n.author;
  paintSheetSave();

  const text = n.body || n.text || "";
  document.getElementById("s-text").innerHTML =
    text ? `<div class="prose">${linkify(text)}</div>` : "";

  document.getElementById("s-mynote").value = mine[id] || "";
  document.getElementById("s-tick").classList.remove("on");
  document.querySelector(".sheet-b").scrollTop = 0;
  sheet.showModal();

  if (!read.has(id)) { read.add(id); save(); refresh(); }
}

/* ── wiring ─────────────────────────────────────────────────────────────── */
function refresh() { renderRail(); renderList(); }

document.addEventListener("click", e => {
  const r = e.target.closest("[data-read]");
  if (r) {
    const id = r.dataset.read;
    read.has(id) ? read.delete(id) : read.add(id);
    save(); refresh(); return;
  }
  const b = e.target.closest("[data-bm]");
  if (b) {
    const id = b.dataset.bm;
    bm.has(id) ? bm.delete(id) : bm.add(id);
    save(); refresh(); return;
  }
  const o = e.target.closest("[data-id]");
  if (o) openNote(o.dataset.id);
});

document.getElementById("bmfilter").addEventListener("click", () => {
  onlyBm = !onlyBm;
  const btn = document.getElementById("bmfilter");
  btn.setAttribute("aria-pressed", onlyBm);
  document.getElementById("bmlabel").textContent = onlyBm ? "Showing saved" : "Bookmarked";
  renderList();
});

document.getElementById("year").addEventListener("change", e => {
  year = e.target.value;
  renderList();
});

document.getElementById("s-save").addEventListener("click", () => {
  if (!openId) return;
  bm.has(openId) ? bm.delete(openId) : bm.add(openId);
  save(); paintSheetSave(); refresh();
});

let noteTimer;
document.getElementById("s-mynote").addEventListener("input", e => {
  if (!openId) return;
  const value = e.target.value;
  clearTimeout(noteTimer);
  noteTimer = setTimeout(() => {
    if (value.trim()) mine[openId] = value;
    else delete mine[openId];
    save();
    const tick = document.getElementById("s-tick");
    tick.classList.add("on");
    setTimeout(() => tick.classList.remove("on"), 1400);
  }, 400);
});

document.getElementById("s-close").addEventListener("click", () => sheet.close());
sheet.addEventListener("click", e => {
  const box = sheet.querySelector(".sheet").getBoundingClientRect();
  if (e.clientY < box.top || e.clientY > box.bottom
   || e.clientX < box.left || e.clientX > box.right) sheet.close();
});

let t;
document.getElementById("q").addEventListener("input", e => {
  clearTimeout(t);
  const v = e.target.value;
  t = setTimeout(() => { query = v.trim(); renderList(); }, 120);
});

renderYears();
refresh();
</script>
"""

# The Artifact publisher supplies its own document skeleton; hosting needs a
# complete document with a charset so the punctuation survives.
SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Felix's weekly market notes for GOAT Academy.">
{body}
</html>
"""


def main() -> int:
    payload = collect()
    html = PAGE.replace("__DATA__", json.dumps(payload, ensure_ascii=False))

    OUT.write_text(SHELL.format(body=html))
    FRAGMENT.parent.mkdir(parents=True, exist_ok=True)
    FRAGMENT.write_text(html)

    print(f"notes:   {len(payload['notes'])}")
    print(f"years:   {', '.join(payload['years'])}")
    print(f"wrote    index.html ({OUT.stat().st_size // 1024} KB) and preview/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
