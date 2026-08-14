#!/usr/bin/env python3
"""Generate a standalone preview of the archive from the real indexed data.

The Next.js app needs a live Supabase project, which makes it hard to show
anyone what the archive actually looks like. This renders the same content as a
single self-contained HTML file so the archive can be reviewed before any
infrastructure exists.

Styled to match the GOAT Academy Trading Roadmap interface. Read state and
bookmarks persist in localStorage, so the preview behaves like the real thing.

Output: preview/index.html
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "notes_index.json"
DOCS = ROOT / "data" / "raw" / "docs"
OUT = ROOT / "index.html"

LINK_LABELS = {
    "source_doc": "Original document",
    "watchlist_sheet": "Watchlist",
    "article": "Full article",
    "heartbeat": "Heartbeat Scanner",
    "video": "Video",
}

MD_NOISE = re.compile(r"[#*_`\[\]()>]|https?://\S+")


def snippet_of(text: str, limit: int = 165) -> str:
    """A clean one-line teaser for the magazine cards."""
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

        notes.append({
            "id": note["post_id"],
            "title": note["title"],
            "date": note.get("note_date"),
            "author": note.get("author") or "Felix Prehn",
            "postUrl": note.get("post_url"),
            "postText": note.get("post_text") or "",
            "body": body,
            "words": len(body.split()) if body else 0,
            "teaser": snippet_of(body or note.get("post_text") or ""),
            "kinds": sorted({l["kind"] for l in links}),
            "links": links,
        })

    # Several weeks share identical wrapper text ("We've updated the format of
    # your weekly notes..."), which would make the latest-notes cards read as
    # five copies of the same thing. Where a teaser is boilerplate, describe
    # what the note actually links to instead.
    counts: dict[str, int] = {}
    for note in notes:
        if note["teaser"]:
            counts[note["teaser"]] = counts.get(note["teaser"], 0) + 1

    for note in notes:
        if note["body"] or counts.get(note["teaser"], 0) <= 2:
            continue
        kinds = {link["kind"] for link in note["links"]}
        parts = []
        if "article" in kinds:
            parts.append("full written commentary")
        if "source_doc" in kinds:
            parts.append("the full write-up")
        if "heartbeat" in kinds:
            parts.append("the Heartbeat Scanner watchlist")
        if "watchlist_sheet" in kinds:
            parts.append("Felix's watchlist")
        if "video" in kinds:
            parts.append("a walkthrough video")

        if parts:
            joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
            note["teaser"] = f"This week's market note, linking to {joined}."
        else:
            note["teaser"] = "This week's market note."

    notes.sort(key=lambda n: (n["date"] or "0000-00-00"), reverse=True)
    years = sorted({n["date"][:4] for n in notes if n["date"]}, reverse=True)

    return {"notes": notes, "years": years, "linkLabels": LINK_LABELS}


HTML = r"""<title>Felix's Notes Archive</title>
<style>
/* ── tokens ─────────────────────────────────────────────────────────────── */
:root {
  --bg: #ffffff;
  --panel: #ffffff;
  --panel-2: #f7f9fa;
  --line: #e3e8ec;
  --line-soft: #eef2f5;
  --ink: #0d1417;
  --ink-2: #46545c;
  --ink-3: #7d8b93;

  --brand: #14639e;          /* display title, active tab */
  --brand-2: #1b9cd8;        /* eyebrows, links, rings */
  --brand-ring: #1b9cd8;
  --green: #17914c;          /* byline, read state */
  --green-soft: #e6f4ec;
  --lime: #c4f135;           /* progress pill */
  --lime-ink: #1c2b06;
  --welcome: #e9f3ef;
  --welcome-line: #cfe3db;
  --mark: #cfeaf7;
  --shadow: 0 1px 2px rgba(13, 20, 23, .05);
  --gold: #b8860b;

  --ui: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
  --read: ui-serif, Georgia, "Iowan Old Style", "Times New Roman", serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #080a0b;
    --panel: #121517;
    --panel-2: #181c1f;
    --line: #262c30;
    --line-soft: #1e2427;
    --ink: #f2f6f8;
    --ink-2: #a8b4bb;
    --ink-3: #77848b;

    --brand: #2fa8e0;
    --brand-2: #35b1e8;
    --brand-ring: #1b9cd8;
    --green: #3ddc84;
    --green-soft: #10281b;
    --lime: #c4f135;
    --lime-ink: #16220a;
    --welcome: #0b2723;
    --welcome-line: #17443c;
    --mark: #123c52;
    --shadow: 0 1px 2px rgba(0, 0, 0, .4);
    --gold: #e0b44c;
  }
}
:root[data-theme="dark"] {
  --bg: #080a0b;
  --panel: #121517;
  --panel-2: #181c1f;
  --line: #262c30;
  --line-soft: #1e2427;
  --ink: #f2f6f8;
  --ink-2: #a8b4bb;
  --ink-3: #77848b;

  --brand: #2fa8e0;
  --brand-2: #35b1e8;
  --brand-ring: #1b9cd8;
  --green: #3ddc84;
  --green-soft: #10281b;
  --lime: #c4f135;
  --lime-ink: #16220a;
  --welcome: #0b2723;
  --welcome-line: #17443c;
  --mark: #123c52;
  --shadow: 0 1px 2px rgba(0, 0, 0, .4);
  --gold: #e0b44c;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--ui);
  font-size: 16px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.strip { height: 30px; background: linear-gradient(90deg,#0c5d5a 0%,#127fae 55%,#29a8e0 100%); }
.wrap { max-width: 78rem; margin: 0 auto; padding: 0 1.5rem; }
button { font: inherit; cursor: pointer; }

/* ── header ─────────────────────────────────────────────────────────────── */
.head { background: var(--panel); }
.head-in { display: flex; align-items: flex-start; gap: 1rem; padding: 1.6rem 0 1.4rem; }
.logo {
  flex: none; width: 58px; height: 58px; border-radius: 15px; display: grid;
  place-items: center; background: linear-gradient(150deg,#29a8e0,#0f6ba6);
  box-shadow: 0 3px 10px rgba(20,99,158,.3);
}
.logo svg { width: 30px; height: 30px; }
.titles { flex: 1; min-width: 0; }
h1 {
  margin: 0; font-size: clamp(1.6rem, 3.4vw, 2.35rem); font-weight: 800;
  line-height: .97; letter-spacing: -.005em; text-transform: uppercase;
  color: var(--brand); text-wrap: balance;
}
.hello { margin: .35rem 0 0; color: var(--ink-3); font-size: .95rem; }
.head-side { display: flex; align-items: center; gap: .7rem; padding-top: .35rem; }
.edition {
  padding: .42rem .85rem; border-radius: 999px; background: var(--green-soft);
  border: 1px solid var(--welcome-line); color: var(--green);
  font-size: .69rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase;
}
.tbtn {
  width: 42px; height: 42px; border-radius: 999px; display: grid; place-items: center;
  background: var(--panel-2); border: 1px solid var(--line); color: var(--ink-2);
}
.tbtn:hover { color: var(--brand-2); border-color: var(--brand-2); }
.tbtn svg { width: 19px; height: 19px; }
.pill-stat {
  padding: .45rem 1rem; border-radius: 999px; background: var(--lime);
  color: var(--lime-ink); font-size: .92rem; font-weight: 800;
  font-variant-numeric: tabular-nums;
}

/* ── tabs ───────────────────────────────────────────────────────────────── */
.tabs { display: flex; gap: 2.2rem; border-bottom: 1px solid var(--line); background: var(--panel); }
.tab {
  padding: .1rem 0 1rem; background: none; border: 0; border-bottom: 3px solid transparent;
  margin-bottom: -1px; color: var(--ink-2); font-size: .84rem; font-weight: 800;
  letter-spacing: .08em; text-transform: uppercase; white-space: nowrap;
}
.tab[aria-selected="true"] { color: var(--brand); border-bottom-color: var(--brand); }
.tab:hover { color: var(--brand); }
.tab .n { margin-left: .4rem; color: var(--ink-3); font-weight: 700; }

/* ── layout ─────────────────────────────────────────────────────────────── */
.cols { display: grid; grid-template-columns: minmax(0,1fr) 20.5rem; gap: 1.5rem; padding: 1.5rem 0 0; align-items: start; }
@media (max-width: 62rem) { .cols { grid-template-columns: minmax(0,1fr); } aside { order: -1; } }

.card { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; box-shadow: var(--shadow); }
.pad { padding: 1.25rem 1.4rem; }

/* welcome */
.welcome { background: var(--welcome); border-color: var(--welcome-line); display: flex; gap: 1.3rem; align-items: center; }
/* Monogram rather than a photo: the artifact CSP blocks external images, so a
   remote avatar would render as a broken tile. */
.avatar {
  flex: none; width: 116px; height: 116px; border-radius: 999px;
  border: 3px solid var(--brand-ring); display: grid; place-items: center;
  background: linear-gradient(150deg,#29a8e0,#0f6ba6); color: #fff;
  font-size: 2.9rem; font-weight: 800; letter-spacing: -.02em;
}
.eyebrow { font-size: .7rem; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; color: var(--brand-2); }
.welcome h2 { margin: .3rem 0 .5rem; font-size: 1.6rem; font-weight: 800; letter-spacing: -.02em; }
.welcome q { display: block; font-family: var(--read); font-style: italic; font-size: 1.02rem; color: var(--ink-2); quotes: '“' '”'; }
.byline { margin: .6rem 0 0; font-size: .72rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--green); }

/* section head */
.sec-head { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; margin: 1.9rem 0 .8rem; }
.sec-head h3 { margin: 0; font-size: 1.12rem; font-weight: 800; letter-spacing: -.01em; }
.sec-head p { margin: 0; color: var(--ink-3); font-size: .85rem; }

/* ── carousel ───────────────────────────────────────────────────────────── */
.rail { display: flex; gap: .9rem; overflow-x: auto; scroll-snap-type: x mandatory; padding: .2rem .2rem 1rem; margin: 0 -.2rem; }
.rail::-webkit-scrollbar { height: 8px; }
.rail::-webkit-scrollbar-thumb { background: var(--line); border-radius: 99px; }
.mag {
  flex: 0 0 17.5rem; scroll-snap-align: start; display: flex; flex-direction: column;
  text-align: left; padding: 1.05rem 1.15rem; border-radius: 15px;
  background: var(--panel); border: 1px solid var(--line); box-shadow: var(--shadow);
  color: inherit; transition: transform .14s ease, border-color .14s ease;
}
.mag:hover { transform: translateY(-3px); border-color: var(--brand-2); }
.mag .k { display: flex; align-items: center; gap: .45rem; font-size: .68rem; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; color: var(--brand-2); }
.mag h4 { margin: .55rem 0 .45rem; font-size: 1.02rem; font-weight: 750; line-height: 1.28; letter-spacing: -.01em; }
.mag p { margin: 0; font-family: var(--read); font-size: .87rem; line-height: 1.5; color: var(--ink-2); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.mag .kinds { display: flex; flex-wrap: wrap; gap: .35rem; }
.mag .kinds i {
  font-style: normal; font-size: .68rem; font-weight: 750; letter-spacing: .04em;
  padding: .22rem .55rem; border-radius: 6px; color: var(--ink-2);
  background: var(--panel-2); border: 1px solid var(--line);
}
.mag .foot { margin-top: .8rem; padding-top: .7rem; border-top: 1px solid var(--line-soft); font-size: .73rem; font-weight: 700; color: var(--ink-3); display: flex; justify-content: space-between; }
.latest { color: var(--lime-ink); background: var(--lime); padding: .1rem .42rem; border-radius: 5px; font-size: .6rem; letter-spacing: .08em; }

/* ── filters ────────────────────────────────────────────────────────────── */
.filters { display: flex; flex-wrap: wrap; gap: .6rem; align-items: center; margin-bottom: 1rem; }
.searchbox { position: relative; flex: 1 1 17rem; }
.searchbox svg { position: absolute; left: .8rem; top: 50%; transform: translateY(-50%); width: 17px; height: 17px; color: var(--ink-3); }
#q {
  width: 100%; padding: .62rem .8rem .62rem 2.3rem; border-radius: 10px;
  background: var(--panel); border: 1px solid var(--line); color: var(--ink); font-size: .92rem;
}
#q:focus { outline: 2px solid var(--brand-2); outline-offset: -1px; }
.chipbar { display: flex; gap: .4rem; flex-wrap: wrap; }
.yr {
  padding: .5rem .9rem; border-radius: 999px; background: var(--panel);
  border: 1px solid var(--line); color: var(--ink-2); font-size: .78rem; font-weight: 750;
}
.yr[aria-pressed="true"] { background: var(--brand); border-color: var(--brand); color: #fff; }
.yr:hover:not([aria-pressed="true"]) { border-color: var(--brand-2); color: var(--brand-2); }

/* ── list ───────────────────────────────────────────────────────────────── */
.list { border-radius: 16px; overflow: hidden; border: 1px solid var(--line); background: var(--panel); }
.ygroup { display: flex; align-items: center; gap: .7rem; padding: .7rem 1.15rem; background: var(--panel-2); border-bottom: 1px solid var(--line); }
.ygroup b { font-size: 1.35rem; font-weight: 800; letter-spacing: -.02em; }
.ygroup span { font-size: .74rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3); }
.row { display: flex; align-items: center; gap: .35rem; border-bottom: 1px solid var(--line-soft); }
.row:last-child { border-bottom: 0; }
.row:hover { background: var(--panel-2); }
.open {
  flex: 1; min-width: 0; display: flex; align-items: center; gap: .9rem;
  padding: .78rem .3rem .78rem 1.15rem; background: none; border: 0; color: inherit; text-align: left;
}
.dot { flex: none; width: 19px; height: 19px; border-radius: 999px; border: 2px solid var(--line); display: grid; place-items: center; }
.dot svg { width: 11px; height: 11px; color: #fff; opacity: 0; }
.is-read .dot { background: var(--green); border-color: var(--green); }
.is-read .dot svg { opacity: 1; }
.d { flex: none; width: 6.4rem; font-size: .82rem; font-weight: 700; color: var(--ink-3); font-variant-numeric: tabular-nums; }
.t { flex: 1; min-width: 0; font-size: .97rem; font-weight: 700; letter-spacing: -.005em; }
.is-read .t { font-weight: 500; color: var(--ink-2); }
.ctx { display: block; margin-top: .18rem; font-family: var(--read); font-size: .84rem;
       font-weight: 400; line-height: 1.45; color: var(--ink-3); }
.mark-btn, .bm-btn {
  flex: none; width: 36px; height: 36px; border-radius: 9px; background: none; border: 0;
  color: var(--ink-3); display: grid; place-items: center;
}
.bm-btn { margin-right: .8rem; }
.mark-btn:hover, .bm-btn:hover { background: var(--line-soft); color: var(--brand-2); }
.mark-btn svg, .bm-btn svg { width: 18px; height: 18px; }
.bm-btn[aria-pressed="true"] { color: var(--gold); }
.bm-btn[aria-pressed="true"] svg { fill: currentColor; }
.empty { padding: 3.5rem 1.5rem; text-align: center; color: var(--ink-3); }
.empty b { display: block; margin-bottom: .3rem; color: var(--ink); font-size: 1.05rem; }

/* ── sidebar ────────────────────────────────────────────────────────────── */
aside { display: grid; gap: 1rem; }
aside h3 { margin: 0 0 .9rem; font-size: 1.02rem; font-weight: 800; }
.big { display: flex; align-items: baseline; gap: .6rem; }
.big b { font-size: 2.5rem; font-weight: 800; letter-spacing: -.03em; line-height: 1; }
.big span { color: var(--ink-3); font-size: .88rem; }
.bars { display: flex; gap: .35rem; margin-top: 1rem; }
.bars div { flex: 1; text-align: center; }
.bars i { display: block; height: 6px; border-radius: 99px; background: var(--line); }
.bars i.on { background: var(--brand-2); }
.bars i.done { background: var(--green); }
.bars em { display: block; margin-top: .45rem; font-size: .68rem; font-weight: 800; letter-spacing: .07em; font-style: normal; color: var(--ink-3); }
.bars div.cur em { color: var(--brand-2); }
.up { display: block; width: 100%; text-align: left; padding: .95rem 1.05rem; border-radius: 12px; background: var(--panel-2); border: 1px solid var(--line); color: inherit; }
.up:hover { border-color: var(--brand-2); }
.up h4 { margin: .35rem 0 .3rem; font-size: 1rem; font-weight: 750; line-height: 1.3; }
.up p { margin: 0 0 .55rem; font-size: .82rem; color: var(--ink-3); }
.up .go { font-size: .78rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--green); }
.reflist { display: grid; }
.reflist a { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: .7rem 0; border-bottom: 1px solid var(--line-soft); color: inherit; text-decoration: none; font-size: .92rem; font-weight: 650; }
.reflist a:last-child { border-bottom: 0; }
.reflist a:hover { color: var(--brand-2); }
.reflist span { color: var(--ink-3); }

/* ── dialog ─────────────────────────────────────────────────────────────── */
dialog {
  width: min(46rem, 94vw); max-height: 88vh; padding: 0; border: 1px solid var(--line);
  border-radius: 18px; background: var(--panel); color: var(--ink);
  box-shadow: 0 24px 60px rgba(0,0,0,.3);
}
dialog::backdrop { background: rgba(4,8,10,.62); }
.sheet { display: flex; flex-direction: column; max-height: 88vh; }
.sheet-h { display: flex; gap: 1rem; align-items: flex-start; padding: 1.4rem 1.6rem 1.1rem; border-bottom: 1px solid var(--line); }
.sheet-h h2 { margin: .32rem 0 .35rem; font-size: 1.5rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.18; }
.sheet-h p { margin: 0; font-size: .83rem; color: var(--ink-3); }
.sheet-acts { display: flex; gap: .4rem; flex: none; }
.sheet-b { padding: 1.3rem 1.6rem 1.7rem; overflow-y: auto; }
.prose { font-family: var(--read); font-size: 1.02rem; line-height: 1.68; white-space: pre-wrap; overflow-wrap: break-word; margin: 0 0 1.3rem; }
.srcbox { padding: 1rem 1.15rem; border-radius: 13px; background: var(--panel-2); border: 1px solid var(--line); margin-bottom: .8rem; }
.srcbox h5 { margin: 0 0 .65rem; font-size: .68rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: var(--ink-3); }
.srcbox ul { margin: 0; padding: 0; list-style: none; display: grid; gap: .45rem; }
.srcbox a { color: var(--brand-2); font-size: .92rem; font-weight: 650; text-decoration: none; }
.srcbox a:hover { text-decoration: underline; }
mark { background: var(--mark); color: inherit; border-radius: 3px; padding: 0 .12em; }

footer { margin-top: 2.5rem; padding: 1.5rem 0 2.5rem; border-top: 1px solid var(--line); color: var(--ink-3); font-size: .82rem; }
footer p { margin: 0 0 .35rem; }
:focus-visible { outline: 2px solid var(--brand-2); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
@media (max-width: 40rem) {
  .head-in { flex-wrap: wrap; }
  .welcome { flex-direction: column; text-align: center; }
  .d { width: 100%; }
  .open { flex-wrap: wrap; gap: .3rem .8rem; }
  .tabs { overflow-x: auto; gap: 1.3rem; }
}
</style>

<div class="strip"></div>

<header class="head">
  <div class="wrap">
    <div class="head-in">
      <div class="logo" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 17l5-5 4 3 6-7"/><path d="M14 8h5v5"/>
        </svg>
      </div>
      <div class="titles">
        <h1>Felix&rsquo;s<br>Market Notes</h1>
        <p class="hello">Welcome back, Giulia</p>
      </div>
      <div class="head-side">
        <span class="edition" id="edition">71 notes</span>
        <button class="tbtn" id="theme" aria-label="Switch theme"></button>
        <span class="pill-stat" id="pct">0%</span>
      </div>
    </div>

    <nav class="tabs" role="tablist">
      <button class="tab" role="tab" data-tab="all" aria-selected="true">All notes <span class="n" id="c-all"></span></button>
      <button class="tab" role="tab" data-tab="unread" aria-selected="false">Unread <span class="n" id="c-unread"></span></button>
      <button class="tab" role="tab" data-tab="bookmarked" aria-selected="false">Bookmarked <span class="n" id="c-bm"></span></button>
    </nav>
  </div>
</header>

<div class="wrap">
  <div class="cols">
    <main>
      <section class="card welcome pad">
        <div class="avatar" aria-hidden="true">F</div>
        <div>
          <span class="eyebrow">The archive</span>
          <h2>Every note, in one place</h2>
          <q>Six months of market calls, sector reads and watchlists &mdash; recovered from
          the community and kept together, wherever you are in your trading journey.</q>
          <p class="byline">&middot; Felix, Founder of GOAT Academy</p>
        </div>
      </section>

      <div class="sec-head">
        <h3>Latest notes</h3>
        <p>The five most recent, newest first</p>
      </div>
      <div class="rail" id="rail"></div>

      <div class="sec-head">
        <h3>Browse the archive</h3>
        <p id="listnote"></p>
      </div>

      <div class="filters">
        <div class="searchbox">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>
          </svg>
          <input id="q" type="search" placeholder="Search notes &mdash; gold, VIX, rotation, breakout&hellip;"
                 aria-label="Search notes" autocomplete="off">
        </div>
        <div class="chipbar" id="years"></div>
      </div>

      <div class="list" id="list"></div>
    </main>

    <aside>
      <section class="card pad">
        <h3>Next up</h3>
        <button class="up" id="nextup"></button>
      </section>

      <section class="card pad">
        <h3>Your reading</h3>
        <div class="big"><b id="bigpct">0%</b><span id="bigsub"></span></div>
        <div class="bars" id="bars"></div>
      </section>

      <section class="card pad">
        <h3>Reference</h3>
        <div class="reflist">
          <a href="https://friends.goatacademy.org/spaces/19161480/content" target="_blank" rel="noopener noreferrer">Notes space <span>&rarr;</span></a>
          <a href="https://breakout.goatacademy.org/" target="_blank" rel="noopener noreferrer">Breakout Tool <span>&rarr;</span></a>
          <a href="https://friends.goatacademy.org/spaces/22780196" target="_blank" rel="noopener noreferrer">Felix&rsquo;s Tools <span>&rarr;</span></a>
        </div>
      </section>
    </aside>
  </div>

  <footer>
    <p>Charts and watchlists live inside the original documents and are preserved as links, so nothing is silently lost.</p>
    <p>Historical market commentary, archived for reference. Not financial advice.</p>
  </footer>
</div>

<dialog id="sheet"><div class="sheet">
  <div class="sheet-h">
    <div style="flex:1;min-width:0">
      <span class="eyebrow" id="s-date"></span>
      <h2 id="s-title"></h2>
      <p id="s-by"></p>
    </div>
    <div class="sheet-acts">
      <button class="bm-btn" id="s-bm" aria-pressed="false" title="Bookmark" style="margin:0"></button>
      <button class="mark-btn" id="s-close" title="Close">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
      </button>
    </div>
  </div>
  <div class="sheet-b" id="s-body"></div>
</div></dialog>

<script>
const DATA = __DATA__;
const NOTES = DATA.notes;
const KEY = "felix-notes-v1";
const SHORT = { source_doc: "Document", watchlist_sheet: "Watchlist",
  article: "Article", heartbeat: "Heartbeat", video: "Video" };

const ICON = {
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.5l5.5 5.5L20 6"/></svg>',
  bookmark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12a1 1 0 011 1v17l-7-4-7 4V4a1 1 0 011-1z"/></svg>',
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.8-7 10-7 10 7 10 7-3.8 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 13A9 9 0 1111 3a7 7 0 0010 10z"/></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>',
};

/* ── state ──────────────────────────────────────────────────────────────── */
let state = { read: [], bm: [], theme: null };
try { Object.assign(state, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
const read = new Set(state.read || []);
const bm = new Set(state.bm || []);
const save = () => {
  try {
    localStorage.setItem(KEY, JSON.stringify({
      read: [...read], bm: [...bm], theme: state.theme,
    }));
  } catch (e) {}
};

let tab = "all";
let year = "all";
let query = "";

/* ── theme ──────────────────────────────────────────────────────────────── */
const themeBtn = document.getElementById("theme");
function isDark() {
  return state.theme ? state.theme === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;
}
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

/* When a note matches on its text rather than its title, show the passage that
   matched — otherwise the row gives no clue why it is in the results. */
function matchLine(n, q) {
  if (!q || n.title.toLowerCase().includes(q.toLowerCase())) return "";
  const hay = n.body || n.postText || "";
  const at = hay.toLowerCase().indexOf(q.toLowerCase());
  if (at < 0) return "";
  const from = Math.max(0, at - 55);
  const raw = (from ? "…" : "") + hay.slice(from, at + q.length + 85).replace(/\s+/g, " ").trim() + "…";
  return `<span class="ctx">${hl(raw, q)}</span>`;
}

const matches = n => {
  if (year !== "all" && (n.date || "").slice(0, 4) !== year) return false;
  if (tab === "unread" && read.has(n.id)) return false;
  if (tab === "bookmarked" && !bm.has(n.id)) return false;
  if (!query) return true;
  const q = query.toLowerCase();
  return n.title.toLowerCase().includes(q)
    || (n.body || "").toLowerCase().includes(q)
    || n.postText.toLowerCase().includes(q);
};

/* ── carousel ───────────────────────────────────────────────────────────── */
function renderRail() {
  document.getElementById("rail").innerHTML = NOTES.slice(0, 5).map((n, i) => `
    <button class="mag" data-id="${esc(n.id)}">
      <span class="k">${i === 0 ? '<span class="latest">Newest</span>' : ""}${fmt(n.date)}</span>
      <h4>${esc(n.title)}</h4>
      ${n.body ? `<p>${esc(n.teaser)}</p>`
        : `<span class="kinds">${n.kinds.map(k =>
            `<i>${esc(SHORT[k] || k)}</i>`).join("")}</span>`}
      <span class="foot"><span>${read.has(n.id) ? "Read" : "Not read"}</span>
      <span>${bm.has(n.id) ? "Bookmarked" : ""}</span></span>
    </button>`).join("");
}

/* ── years ──────────────────────────────────────────────────────────────── */
function renderYears() {
  const all = [["all", "All years"], ...DATA.years.map(y => [y, y])];
  document.getElementById("years").innerHTML = all.map(([v, label]) => {
    const n = v === "all" ? NOTES.length
      : NOTES.filter(x => (x.date || "").slice(0, 4) === v).length;
    return `<button class="yr" data-year="${v}" aria-pressed="${year === v}">${label} <span style="opacity:.6">${n}</span></button>`;
  }).join("");
}

/* ── list ───────────────────────────────────────────────────────────────── */
function renderList() {
  const hits = NOTES.filter(matches);
  const el = document.getElementById("list");

  document.getElementById("listnote").textContent =
    `${hits.length} of ${NOTES.length} notes shown`;

  if (!hits.length) {
    el.innerHTML = `<div class="empty"><b>Nothing here yet</b>
      ${tab === "bookmarked" ? "Bookmark a note with the flag icon and it will appear here."
        : tab === "unread" ? "You have read everything that matches these filters."
        : "Try a different search or year."}</div>`;
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
      <div class="row ${read.has(n.id) ? "is-read" : ""}" data-row="${esc(n.id)}">
        <button class="open" data-id="${esc(n.id)}">
          <span class="dot">${ICON.check}</span>
          <span class="d">${fmt(n.date)}</span>
          <span class="t">${hl(n.title, query)}${matchLine(n, query)}</span>
        </button>
        <button class="mark-btn" data-toggle-read="${esc(n.id)}"
          title="${read.has(n.id) ? "Mark as unread" : "Mark as read"}">${ICON.eye}</button>
        <button class="bm-btn" data-toggle-bm="${esc(n.id)}" aria-pressed="${bm.has(n.id)}"
          title="Bookmark">${ICON.bookmark}</button>
      </div>`).join("")}`).join("");
}

/* ── counters + sidebar ─────────────────────────────────────────────────── */
function renderMeta() {
  const total = NOTES.length;
  const nRead = NOTES.filter(n => read.has(n.id)).length;
  const pct = total ? Math.round((nRead / total) * 100) : 0;

  document.getElementById("pct").textContent = pct + "%";
  document.getElementById("bigpct").textContent = pct + "%";
  document.getElementById("bigsub").textContent = `${nRead} of ${total} notes read`;
  document.getElementById("c-all").textContent = total;
  document.getElementById("c-unread").textContent = total - nRead;
  document.getElementById("c-bm").textContent = bm.size;
  document.getElementById("edition").textContent = total + " notes";

  document.getElementById("bars").innerHTML = DATA.years.slice().reverse().map(y => {
    const inYear = NOTES.filter(n => (n.date || "").slice(0, 4) === y);
    const done = inYear.filter(n => read.has(n.id)).length;
    const cls = done === inYear.length ? "done" : done > 0 ? "on" : "";
    return `<div class="${done > 0 && done < inYear.length ? "cur" : ""}">
      <i class="${cls}"></i><em>${y}</em></div>`;
  }).join("");

  const next = NOTES.find(n => !read.has(n.id));
  const up = document.getElementById("nextup");
  if (next) {
    up.dataset.id = next.id;
    up.innerHTML = `<span class="eyebrow">Note</span><h4>${esc(next.title)}</h4>
      <p>${fmtLong(next.date)}</p><span class="go">Read it &rarr;</span>`;
    up.style.display = "";
  } else {
    up.style.display = "none";
  }
}

/* ── detail ─────────────────────────────────────────────────────────────── */
const sheet = document.getElementById("sheet");
let openId = null;

function paintSheetBm() {
  const btn = document.getElementById("s-bm");
  btn.innerHTML = ICON.bookmark;
  btn.setAttribute("aria-pressed", bm.has(openId));
}

function openNote(id) {
  const n = NOTES.find(x => x.id === id);
  if (!n) return;
  openId = id;

  document.getElementById("s-date").textContent = fmtLong(n.date);
  document.getElementById("s-title").textContent = n.title;
  document.getElementById("s-by").textContent =
    n.author + (n.words ? ` · ${n.words.toLocaleString()} words` : "");
  paintSheetBm();

  const links = n.links.map(l =>
    `<li><a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${
      esc(DATA.linkLabels[l.kind] || "Link")} &rarr;</a></li>`).join("");

  document.getElementById("s-body").innerHTML = [
    n.body ? `<div class="prose">${esc(n.body)}</div>`
           : (n.postText ? `<div class="prose">${esc(n.postText)}</div>` : ""),
    links ? `<div class="srcbox"><h5>Original sources</h5><ul>${links}</ul></div>` : "",
    n.postUrl ? `<div class="srcbox"><h5>In the community</h5><ul><li>
        <a href="${esc(n.postUrl)}" target="_blank" rel="noopener noreferrer">Open the original post &rarr;</a>
      </li></ul></div>` : "",
  ].join("");

  document.getElementById("s-body").scrollTop = 0;
  sheet.showModal();

  if (!read.has(id)) { read.add(id); save(); refresh(); }
}

/* ── wiring ─────────────────────────────────────────────────────────────── */
function refresh() { renderRail(); renderList(); renderMeta(); }

document.addEventListener("click", e => {
  const openBtn = e.target.closest("[data-id]");
  const readBtn = e.target.closest("[data-toggle-read]");
  const bmBtn = e.target.closest("[data-toggle-bm]");
  const yrBtn = e.target.closest("[data-year]");
  const tabBtn = e.target.closest("[data-tab]");

  if (readBtn) {
    const id = readBtn.dataset.toggleRead;
    read.has(id) ? read.delete(id) : read.add(id);
    save(); refresh(); return;
  }
  if (bmBtn) {
    const id = bmBtn.dataset.toggleBm;
    bm.has(id) ? bm.delete(id) : bm.add(id);
    save(); refresh(); return;
  }
  if (yrBtn) {
    year = yrBtn.dataset.year;
    renderYears(); renderList(); return;
  }
  if (tabBtn) {
    tab = tabBtn.dataset.tab;
    document.querySelectorAll("[data-tab]").forEach(b =>
      b.setAttribute("aria-selected", b.dataset.tab === tab));
    renderList(); return;
  }
  if (openBtn && openBtn.dataset.id) openNote(openBtn.dataset.id);
});

document.getElementById("s-bm").addEventListener("click", () => {
  if (!openId) return;
  bm.has(openId) ? bm.delete(openId) : bm.add(openId);
  save(); paintSheetBm(); refresh();
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


# Standalone wrapper for hosting (Vercel). The Artifact publisher supplies its
# own document skeleton, so it gets the bare fragment instead.
SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Felix's weekly market notes for GOAT Academy — searchable archive.">
{body}
</html>
"""


def main() -> int:
    payload = collect()
    html = HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(SHELL.format(body=html))

    # Fragment for the Artifact preview, which adds its own <head>/<body>.
    fragment = ROOT / "preview" / "index.html"
    fragment.parent.mkdir(parents=True, exist_ok=True)
    fragment.write_text(html)

    with_body = [n for n in payload["notes"] if n["body"]]
    print(f"notes:      {len(payload['notes'])} weekly ({len(with_body)} with full text)")
    print(f"years:      {', '.join(payload['years'])}")
    print(f"wrote       {OUT.relative_to(ROOT)}  ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
