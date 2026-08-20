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
  --bg: #e6eef4;
  --panel: #ffffff;
  --panel-2: #f2f7fa;
  --line: #c8dae5;
  --line-strong: #9bbccf;
  --ink: #04131a;
  --ink-2: #33525f;
  --ink-3: #5d7d8c;

  --brand: #0a5f92;
  --brand-2: #0d7d99;
  --green: #14834a;
  --gold: #92640a;
  --mark: #96dff3;
  --tintbar: #dceaf2;
  --shadow: 0 1px 2px rgba(4, 19, 26, .06);
  --shadow-lift: 0 14px 34px -14px rgba(4, 19, 26, .35);
  --brandgrad: linear-gradient(140deg,#0d4a52 0%,#12566d 55%,#175f80 100%);

  /* One clean sans throughout — the serif was harder on the eye at length. */
  --ui: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #07090a;
    --panel: #101416;
    --panel-2: #171d21;
    --line: #242e33;
    --line-strong: #33424a;
    --ink: #f1f6f8;
    --ink-2: #a4b2b9;
    --ink-3: #75858d;

    --brand: #2fa8e0;
    --brand-2: #38b8dd;
    --green: #3ddc84;
    --gold: #d8a949;
    --mark: #0f4257;
    --tintbar: #17242a;
    --shadow: 0 1px 2px rgba(0, 0, 0, .5);
    --shadow-lift: 0 12px 30px -14px rgba(0, 0, 0, .85);
    --brandgrad: linear-gradient(140deg,#0c3d44 0%,#0f4a5c 55%,#13566e 100%);
  }
}
:root[data-theme="dark"] {
  --bg: #07090a;
  --panel: #101416;
  --panel-2: #171d21;
  --line: #242e33;
  --line-strong: #33424a;
  --ink: #f1f6f8;
  --ink-2: #a4b2b9;
  --ink-3: #75858d;

  --brand: #2fa8e0;
  --brand-2: #38b8dd;
  --green: #3ddc84;
  --gold: #d8a949;
  --mark: #0f4257;
  --tintbar: #17242a;
  --shadow: 0 1px 2px rgba(0, 0, 0, .5);
  --shadow-lift: 0 12px 30px -14px rgba(0, 0, 0, .85);
  --brandgrad: linear-gradient(140deg,#0c3d44 0%,#0f4a5c 55%,#13566e 100%);
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
.banner-in { display: flex; align-items: center; gap: 1.1rem; padding: 1.6rem 0 1.7rem; }
.mark {
  flex: none; width: 54px; height: 54px; border-radius: 14px; display: grid;
  place-items: center; background: rgba(255,255,255,.15);
  border: 1px solid rgba(255,255,255,.3);
}
.mark svg { width: 27px; height: 27px; }
.banner h1 {
  margin: 0; font-size: clamp(1.3rem, 2.6vw, 1.72rem); font-weight: 600;
  line-height: 1.1; letter-spacing: .012em; text-transform: uppercase;
  text-wrap: balance;
}
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
.topgap { height: 1.8rem; }
.filters { margin-top: 1.8rem; }

/* ── latest: one lead note, four stacked beside it ─────────────────────── */
/* Equal-weight cards gave the eye nothing to land on. A dominant lead with a
   secondary column is how a front page carries hierarchy. */
.latest { display: grid; grid-template-columns: 1.55fr 1fr; gap: 1.1rem; align-items: stretch; }
@media (max-width: 52rem) { .latest { grid-template-columns: 1fr; } }

.lead {
  position: relative; overflow: hidden;
  display: flex; flex-direction: column; text-align: left; color: #fff;
  padding: 1.7rem 1.8rem; border-radius: 18px; background: var(--brandgrad);
  border: 1px solid var(--line); box-shadow: var(--shadow);
  transition: box-shadow .18s ease, transform .18s ease;
}
.lead:hover { transform: translateY(-2px); box-shadow: var(--shadow-lift); }
.lead .kicker, .lead h3, .lead p, .lead .go { position: relative; }
.kicker {
  display: inline-flex; align-items: center; gap: .5rem; font-size: .69rem;
  font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--brand-2);
}
.kicker::before { content: ""; width: 1.6rem; height: 2px; background: currentColor; border-radius: 2px; }
.lead .kicker { color: #fff; }
.lead h3 {
  margin: .85rem 0 .6rem; font-size: clamp(1.35rem, 2.5vw, 1.72rem); font-weight: 800;
  line-height: 1.18; letter-spacing: -.024em; text-wrap: balance;
}
.lead p { margin: 0; font-size: .96rem; line-height: 1.62; color: rgba(255,255,255,.9);
  display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.lead .go {
  margin-top: auto; padding-top: 1.1rem; font-size: .8rem; font-weight: 750;
  letter-spacing: .04em; color: #fff; display: inline-flex; align-items: center; gap: .4rem;
}
.lead:hover .go { gap: .6rem; }

.stack { display: flex; flex-direction: column; border: 1px solid var(--line); border-radius: 18px; background: var(--panel); overflow: hidden; }
.stack-h {
  padding: .8rem 1.15rem; border-bottom: 1px solid var(--line); background: var(--tintbar);
  font-size: .67rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--ink-3);
}
.mini {
  flex: 1; display: flex; flex-direction: column; justify-content: center; gap: .22rem;
  padding: .8rem 1.15rem; text-align: left; background: none; border: 0;
  border-bottom: 1px solid var(--line); color: inherit;
}
.mini:last-child { border-bottom: 0; }
.mini:hover { background: var(--panel-2); }
.mini .when { font-size: .69rem; font-weight: 750; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-3); font-variant-numeric: tabular-nums; }
.mini h4 { margin: 0; font-size: .92rem; font-weight: 700; line-height: 1.32; letter-spacing: -.01em;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

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
/* The archive as a board: a tinted canvas, one band per year, and inside it
   the months as colour-coded groups of card rows — date, note, then a Status
   and a Saved block per row, the way a work board reads state at a glance. */
.list { padding: .9rem; border: 1px solid var(--line); border-radius: 16px; background: var(--panel-2); }
.ymod + .ymod { margin-top: 1.1rem; }
.yband {
  display: flex; align-items: center; gap: .65rem; width: 100%; padding: .74rem 1rem;
  border: 0; border-radius: 12px; background: var(--brandgrad); color: #fff;
  text-align: left; position: sticky; top: .5rem; z-index: 2; box-shadow: var(--shadow);
}
.yband:hover { filter: brightness(1.07); }
.chev { flex: none; width: 16px; height: 16px; color: rgba(255,255,255,.85); transition: transform .16s ease; }
.yband[aria-expanded="false"] .chev { transform: rotate(-90deg); }
.yband b { font-size: 1.05rem; font-weight: 800; letter-spacing: .02em; }
.yband .tally {
  margin-left: auto; padding: .28rem .7rem; border-radius: 999px;
  background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.25);
  font-size: .72rem; font-weight: 700; letter-spacing: .02em; white-space: nowrap;
}

/* Each month carries one accent (--acc) that colours its heading and the edge
   of every row beneath it, so a scan down the page reads month by month. */
.mgroup { margin: 1.1rem .1rem 0; }
.mhead {
  display: grid; grid-template-columns: minmax(0,1fr) 7rem 6.2rem; gap: .5rem 1rem;
  align-items: end; padding: 0 .95rem .4rem calc(.95rem + 6px);
}
.mhead h3 {
  margin: 0; font-size: .95rem; font-weight: 800; letter-spacing: -.01em;
  color: color-mix(in srgb, var(--acc) 72%, var(--ink));
}
.mhead h3 span { margin-left: .55rem; font-size: .72rem; font-weight: 700; color: var(--ink-3); }
.clab {
  font-size: .66rem; font-weight: 750; letter-spacing: .09em; text-transform: uppercase;
  color: var(--ink-3); text-align: center;
}

.mrow {
  display: grid; grid-template-columns: 4.6rem minmax(0,1fr) 7rem 6.2rem;
  grid-template-areas: "d t st sv"; gap: .5rem 1rem; align-items: center;
  padding: .5rem .95rem; margin-top: .4rem;
  border: 1px solid var(--line); border-left: 6px solid var(--acc);
  border-radius: 10px; background: var(--panel); box-shadow: var(--shadow);
  transition: box-shadow .15s ease, transform .15s ease;
}
.mrow:hover { transform: translateY(-1px); box-shadow: var(--shadow-lift); }
.d {
  grid-area: d; font-size: .8rem; font-weight: 750; color: var(--ink-3);
  font-variant-numeric: tabular-nums; letter-spacing: .01em; white-space: nowrap;
}
.open { grid-area: t; min-width: 0; padding: .3rem 0; background: none; border: 0; color: inherit; text-align: left; }
.open:hover .t { text-decoration: underline; text-underline-offset: 3px; }
.t { display: block; font-size: .98rem; font-weight: 700; line-height: 1.35; letter-spacing: -.012em; }
.is-read .t { font-weight: 550; color: var(--ink-2); }
.ctx { display: block; margin-top: .25rem; font-size: .84rem; font-weight: 400; line-height: 1.5; color: var(--ink-2); }

/* Status and Saved are solid colour blocks in the manner of a board — and
   each block is also the button that toggles its own state. */
.pill {
  padding: .42rem .5rem; border-radius: 7px; border: 1.5px solid var(--line-strong);
  background: var(--panel); color: var(--ink-3); font-size: .76rem; font-weight: 750;
  display: inline-flex; align-items: center; justify-content: center; gap: .34rem;
  white-space: nowrap; transition: background .15s, color .15s, border-color .15s;
}
.pill svg { width: 13px; height: 13px; }
.p-read { grid-area: st; }
.p-save { grid-area: sv; }
.p-read:hover { border-color: #00c875; }
.p-save:hover { border-color: #fdab3d; }
.pill[aria-pressed="true"]:hover { filter: brightness(.96); }
.p-read[aria-pressed="true"] { background: #00c875; border-color: #00c875; color: #03361d; }
.p-save[aria-pressed="true"] { background: #fdab3d; border-color: #fdab3d; color: #4a2c00; }
.p-save[aria-pressed="true"] svg { fill: currentColor; }

/* The compact save button in the reader sheet. */
.save {
  display: inline-flex; align-items: center; gap: .35rem; padding: .4rem .75rem;
  border-radius: 8px; background: transparent; border: 1px solid var(--line-strong);
  color: var(--ink-3); font-size: .76rem; font-weight: 700;
  transition: color .15s, border-color .15s;
}
.save svg { width: 14px; height: 14px; }
.save:hover { border-color: var(--gold); color: var(--gold); }
.save[aria-pressed="true"] { color: var(--gold); border-color: var(--gold); }
.save[aria-pressed="true"] svg { fill: currentColor; }

.empty { padding: 3.4rem 1.5rem; text-align: center; color: var(--ink-3); }
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
  font-size: 1.06rem; line-height: 1.7; letter-spacing: .002em;
  overflow-wrap: break-word; margin: 0 0 1.4rem; color: var(--ink);
}
.prose p { margin: 0 0 .9em; }
.prose p:last-child { margin-bottom: 0; }
.prose strong { font-weight: 800; }
.prose a { color: var(--brand-2); font-weight: 600; overflow-wrap: anywhere; }

/* The week's links, lifted above the blurb so they are the first thing
   reachable rather than buried at the bottom of the post. */
.toplinks { display: grid; gap: .5rem; margin: 0 0 1.15rem; }
.rule { height: 1px; margin: 0 0 1.15rem; border: 0; background: var(--line); }
.tl {
  display: grid; grid-template-columns: 1fr auto; align-items: center; gap: .12rem .8rem;
  padding: .85rem 1.05rem; border-radius: 12px; text-decoration: none;
  background: var(--panel-2); border: 1px solid var(--line); color: var(--ink);
  transition: border-color .15s ease, background .15s ease;
}
.tl:hover { border-color: var(--brand-2); background: var(--tintbar); }
.tl b { font-size: 1rem; font-weight: 800; letter-spacing: -.01em; }
.tl span {
  grid-column: 1; font-size: .8rem; color: var(--ink-3);
  overflow-wrap: anywhere; line-height: 1.4;
}
.tl svg { grid-row: 1 / span 2; grid-column: 2; width: 18px; height: 18px; color: var(--brand-2); }
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
  .list { padding: .6rem; }
  .mhead { grid-template-columns: 1fr; padding-left: calc(.8rem + 6px); }
  .clab { display: none; }
  .mrow {
    grid-template-columns: 1fr auto auto; grid-template-areas: "d st sv" "t t t";
    row-gap: .2rem; padding: .6rem .8rem;
  }
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
  <div class="topgap"></div>
  <div class="latest" id="latest"></div>

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
    <p>Historical market commentary, archived for reference. Not financial advice.
       Topic titles are illustrative samples for this preview.</p>
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
      <button class="save" id="s-save" aria-pressed="false" title="Save this note"></button>
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

/* Illustrative topic titles, keyed by date. Every real post is titled
   "Felix's notes for <date>", which makes the list read as a wall of dates —
   these placeholders show what the archive looks like once real topics are
   extracted from the note bodies. Swap or drop entries freely; a date without
   an entry falls back to the post's own title. */
const SAMPLE_TOPICS = {
  "2025-04-07": "Tariff shock week: reading panic without joining it",
  "2025-04-09": "Midweek special: making sense of a violent reversal",
  "2025-04-10": "Follow-up: what the whipsaw means for your watchlist",
  "2025-04-14": "Earnings season opens — banks set the tone",
  "2025-04-21": "Dollar drift and the case for quality names",
  "2025-04-23": "Midweek check: megacap earnings expectations",
  "2025-04-28": "A quieter grind higher as breadth improves",
  "2025-05-05": "Fed week: patience is a position",
  "2025-05-12": "Relief rally — what to trim, what to keep",
  "2025-05-19": "Bond market noise vs. the real yield signal",
  "2025-05-26": "Holiday-shortened week, full-size setups",
  "2025-06-01": "June playbook: rotation over chasing",
  "2025-06-09": "Inflation week: the setup into CPI",
  "2025-06-15": "Oil spikes and stress-testing the portfolio",
  "2025-06-22": "Risk-off refresher: know where your exits are",
  "2025-06-29": "Half-time report: winners, laggards, lessons",
  "2025-07-06": "New highs on thin volume — trust but verify",
  "2025-07-13": "Bank earnings and the health of the consumer",
  "2025-07-20": "Small caps stir: rotation or head fake?",
  "2025-07-27": "Big tech week: capex is the story",
  "2025-08-03": "Jobs wobble brings recession chatter back",
  "2025-08-10": "Buying fear: the levels that matter",
  "2025-08-17": "Jackson Hole preview: what could change the trend",
  "2025-08-24": "The rate-cut trade after Powell's tone shift",
  "2025-08-31": "September setup: seasonally weak, tactically ready",
  "2025-09-07": "Payrolls and the soft-landing question",
  "2025-09-14": "Cut week: how markets trade the first move",
  "2025-09-21": "After the cut — follow-through or fade?",
  "2025-09-28": "Quarter-end flows and window dressing",
  "2025-10-05": "Q4 kickoff: the seasonal tailwind arrives",
  "2025-10-13": "Earnings season: guidance beats the headline",
  "2025-10-14": "Watchlist refresh — five setups worth stalking",
  "2025-10-19": "Gold's quiet breakout gets loud",
  "2025-10-26": "Megacap earnings marathon: what actually matters",
  "2025-11-02": "Breadth check: the rally beneath the rally",
  "2025-11-09": "Melt-up mechanics — respecting a strong tape",
  "2025-11-16": "AI trade at a crossroads into chip earnings",
  "2025-11-23": "Thanksgiving tape: light volume, real moves",
  "2025-12-07": "Santa rally checklist: what history says",
  "2025-12-14": "The year's final Fed meeting — positioning",
  "2025-12-21": "Year-end review: the trades that taught the most",
  "2026-01-04": "New year, same rules: process over prediction",
  "2026-01-11": "January's early leaders — and the traps",
  "2026-01-18": "Earnings season opens: banks first, guidance first",
  "2026-01-25": "Megacap week: can results carry the multiple?",
  "2026-02-01": "Jobs Friday: good news is good news again",
  "2026-02-08": "Chasing strength vs. buying the pullback",
  "2026-02-15": "CPI week and the last mile of inflation",
  "2026-02-22": "Chip earnings: the market's report card",
  "2026-03-02": "March check-in: leadership keeps rotating",
  "2026-03-08": "Volatility returns — the plan beats the panic",
  "2026-03-16": "Fed week: dots, cuts and the dollar",
  "2026-03-22": "Quad witching aftermath, quarter-end flows",
  "2026-03-29": "Q1 wrap: what worked, what didn't, what's next",
  "2026-04-05": "Q2 kickoff — the earnings bar for a tired tape",
  "2026-04-12": "Bank earnings and the credit pulse",
  "2026-04-19": "Anatomy of a pullback: healthy or not?",
  "2026-04-26": "Big tech earnings: margins do the talking",
  "2026-05-03": "Sell in May? The data behind the cliché",
  "2026-05-10": "Rates reprice — bonds move first, stocks follow",
  "2026-05-17": "New highs, narrow breadth: handle with care",
  "2026-05-24": "Memorial Day week: quiet tape, loud setups",
  "2026-06-07": "Summer rotation: value's turn?",
  "2026-06-14": "Triple witching meets the June Fed meeting",
  "2026-06-21": "Defensives lead — what that usually signals",
  "2026-06-28": "Half-year review: grading the playbook",
  "2026-07-12": "Earnings warm-up: resetting the watchlist",
  "2026-07-18": "Breakout prices: where the scanner is pointing",
  "2026-07-25": "Megacap earnings: AI spend meets AI revenue",
  "2026-08-01": "August opens: jobs data and two fresh setups",
  "2026-08-08": "A new format for your notes — meet the Heartbeat Scanner",
};
NOTES.forEach(n => { n.topic = SAMPLE_TOPICS[n.date] || null; });

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

/* Only the newest year starts open so the page is not one endless list.
   Search and the saved filter look through collapsed years, so a match can
   never hide behind a closed one. */
const collapsed = new Set(DATA.years.slice(1));
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
/* Rows sit under year and month headers, so they carry the day alone. */
const fmtDay = d => d ? new Date(d + "T00:00:00Z").toLocaleDateString("en-GB",
  { day: "numeric", month: "short", timeZone: "UTC" }) : "Undated";
const fmtMonth = m => m === "undated" ? "Undated"
  : new Date(m + "-01T00:00:00Z").toLocaleDateString("en-GB",
    { month: "long", year: "numeric", timeZone: "UTC" });

/* One accent per calendar month, cycled so neighbouring months never match
   and a month keeps its colour from one year to the next. */
const ACCENTS = ["#0073ea", "#00c875", "#a25ddc", "#fdab3d", "#e2445c", "#00b5c4"];
const accent = m => m === "undated" ? "#8a93a6"
  : ACCENTS[(+m.slice(5, 7) - 1) % ACCENTS.length];

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

/* Felix puts the week's links at the foot of the post, under the blurb.
   Readers want them first, so lift any line that is just "Label: URL" to the
   top. The length guard stops a sentence that merely ends in a URL from being
   mistaken for a link line. */
function splitLinks(text) {
  const links = [], prose = [];
  for (const raw of (text || "").split(/\r?\n/)) {
    const line = raw.trim();
    const m = line.match(/^(.{0,60}?)[\s:–—-]*\s*(https?:\/\/\S+)\s*$/);
    if (m && m[2]) {
      const label = m[1].replace(/[\s:–—-]+$/, "").trim();
      links.push({ label: label || "Open the note", url: m[2] });
    } else if (line) {
      prose.push(line);
    }
  }
  return { links, prose: prose.join("\n") };
}

/* When a note matches on its text rather than its title, show the passage that
   matched — otherwise the row gives no clue why it is in the results. */
function matchLine(n, q) {
  if (!q || (n.topic || n.title).toLowerCase().includes(q.toLowerCase())) return "";
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
    || (n.topic || "").toLowerCase().includes(q)
    || (n.body || "").toLowerCase().includes(q)
    || n.text.toLowerCase().includes(q);
};

/* ── latest ─────────────────────────────────────────────────────────────── */
function renderLatest() {
  const [lead, ...rest] = NOTES.slice(0, 5);
  if (!lead) { document.getElementById("latest").innerHTML = ""; return; }

  document.getElementById("latest").innerHTML = `
    <button class="lead" data-id="${esc(lead.id)}">
      <span class="kicker">Newest &middot; ${fmt(lead.date)}</span>
      <h3>${esc(lead.topic || lead.title)}</h3>
      <p>${esc(lead.recap)}</p>
      <span class="go">Read the note &rarr;</span>
    </button>
    <div class="stack">
      <div class="stack-h">Also recent</div>
      ${rest.map(n => `
        <button class="mini" data-id="${esc(n.id)}">
          <span class="when">${fmt(n.date)}</span>
          <h4>${esc(n.topic || n.title)}</h4>
        </button>`).join("")}
    </div>`;
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
  if (!hits.length) {
    el.innerHTML = `<div class="empty"><b>Nothing to show</b>${
      onlyBm ? "Save a note and it will appear here." : "Try a different search or year."}</div>`;
    return;
  }

  /* Year, then month within the year — both arrive newest first. */
  const years = new Map();
  for (const n of hits) {
    const y = n.date ? n.date.slice(0, 4) : "Undated";
    const m = n.date ? n.date.slice(0, 7) : "undated";
    if (!years.has(y)) years.set(y, new Map());
    const months = years.get(y);
    if (!months.has(m)) months.set(m, []);
    months.get(m).push(n);
  }

  const expanded = y => query !== "" || onlyBm || !collapsed.has(y);

  el.innerHTML = [...years].map(([y, months]) => {
    const all = [...months.values()].flat();
    const done = all.filter(n => read.has(n.id)).length;
    return `
    <section class="ymod">
      <button class="yband" data-year-toggle="${y}" aria-expanded="${expanded(y)}">
        <svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
          stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
        <b>${y}</b>
        <span class="tally">${all.length} note${all.length === 1 ? "" : "s"}${
          done ? ` &middot; ${done} read` : ""}</span>
      </button>
      ${!expanded(y) ? "" : [...months].map(([m, rows]) => `
      <section class="mgroup" style="--acc:${accent(m)}">
        <div class="mhead">
          <h3>${fmtMonth(m)}<span>${rows.length}</span></h3>
          <span class="clab" aria-hidden="true">Status</span>
          <span class="clab" aria-hidden="true">Saved</span>
        </div>
        ${rows.map(n => `
        <div class="mrow${read.has(n.id) ? " is-read" : ""}">
          <span class="d">${fmtDay(n.date)}</span>
          <button class="open" data-id="${esc(n.id)}">
            <span class="t">${hl(n.topic || n.title, query)}</span>
            ${matchLine(n, query)}
          </button>
          <button class="pill p-read" data-read="${esc(n.id)}" role="checkbox"
            aria-checked="${read.has(n.id)}" aria-pressed="${read.has(n.id)}"
            title="${read.has(n.id) ? "Mark as unread" : "Mark as read"}">
            ${read.has(n.id) ? ICON.check + "Read" : "Unread"}</button>
          <button class="pill p-save" data-bm="${esc(n.id)}" aria-pressed="${bm.has(n.id)}"
            title="${bm.has(n.id) ? "Remove from saved" : "Save this note"}">
            ${ICON.bookmark}${bm.has(n.id) ? "Saved" : "Save"}</button>
        </div>`).join("")}
      </section>`).join("")}
    </section>`;
  }).join("");
}

/* ── detail ─────────────────────────────────────────────────────────────── */
const sheet = document.getElementById("sheet");

let openId = null;

function paintSheetSave() {
  const btn = document.getElementById("s-save");
  btn.innerHTML = ICON.bookmark + (bm.has(openId) ? "Saved" : "Save");
  btn.setAttribute("aria-pressed", bm.has(openId));
}

/* The community posts arrive as bare newlines with nothing between the lines,
   which read as one compacted block. Give every line its own paragraph, and
   bold the two weekly lead-ins — Felix's Notes and the Heartbeat Scanner — so
   the two-links-a-week format reads as a list rather than a wall. */
function noteHtml(text) {
  return text.split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => `<p>${linkify(line).replace(
      /(Felix[’']s Notes|Heartbeat Scanner)(?=\s*[–—:-])/g,
      "<strong>$1</strong>")}</p>`)
    .join("");
}

function openNote(id) {
  const n = NOTES.find(x => x.id === id);
  if (!n) return;
  openId = id;

  document.getElementById("s-when").textContent = fmtLong(n.date);
  document.getElementById("s-title").textContent = n.topic || n.title;
  document.getElementById("s-by").textContent =
    n.topic ? `${n.author} · ${n.title}` : n.author;
  paintSheetSave();

  const { links, prose } = splitLinks(n.body || n.text || "");
  const linkBlock = links.length ? `<div class="toplinks">${links.map(l => `
    <a class="tl" href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">
      <b>${esc(l.label)}</b>
      <span>${esc(l.url)}</span>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
        stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h13M12 5l7 7-7 7"/></svg>
    </a>`).join("")}</div>` : "";

  document.getElementById("s-text").innerHTML =
    linkBlock
    + (linkBlock && prose ? `<hr class="rule">` : "")
    + (prose ? `<div class="prose">${noteHtml(prose)}</div>` : "");

  document.getElementById("s-mynote").value = mine[id] || "";
  document.getElementById("s-tick").classList.remove("on");
  document.querySelector(".sheet-b").scrollTop = 0;
  sheet.showModal();

  if (!read.has(id)) { read.add(id); save(); refresh(); }
}

/* ── wiring ─────────────────────────────────────────────────────────────── */
function refresh() { renderLatest(); renderList(); }

document.addEventListener("click", e => {
  const r = e.target.closest("[data-read]");
  if (r) {
    const id = r.dataset.read;
    read.has(id) ? read.delete(id) : read.add(id);
    save(); refresh(); return;
  }
  const yt = e.target.closest("[data-year-toggle]");
  if (yt) {
    const y = yt.dataset.yearToggle;
    collapsed.has(y) ? collapsed.delete(y) : collapsed.add(y);
    renderList(); return;
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
  /* Filtering to a year is a request to see it — never a collapsed header. */
  if (year !== "all") collapsed.delete(year);
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
