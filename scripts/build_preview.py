#!/usr/bin/env python3
"""Generate a standalone preview of the archive from the real indexed data.

The Next.js app needs a live Supabase project, which makes it hard to show
anyone what the archive actually looks like. This renders the same content as a
single self-contained HTML file so the archive can be reviewed before any
infrastructure exists.

Output: preview/index.html
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "notes_index.json"
DOCS = ROOT / "data" / "raw" / "docs"
OUT = ROOT / "preview" / "index.html"

LINK_LABELS = {
    "source_doc": "Original document",
    "watchlist_sheet": "Watchlist",
    "article": "Full article",
    "heartbeat": "Heartbeat Scanner",
    "video": "Video",
}


def collect() -> dict:
    index = json.loads(INDEX.read_text())
    notes = []

    for note in index["notes"]:
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
            "kind": note.get("kind"),
            "source": note.get("source_type"),
            "author": note.get("author"),
            "postUrl": note.get("post_url"),
            "postText": note.get("post_text") or "",
            "body": body,
            "words": len(body.split()) if body else 0,
            "links": links,
        })

    notes.sort(key=lambda n: (n["date"] or "0000-00-00"), reverse=True)
    return {
        "notes": notes,
        "skippedWeeks": index.get("skipped_weeks", []),
        "linkLabels": LINK_LABELS,
    }


HTML = """<title>Felix's Notes Archive</title>
<style>
:root {
  --ground: #f1f4f1;
  --surface: #ffffff;
  --surface-2: #e9eee9;
  --ink: #14181a;
  --muted: #5d6a65;
  --faint: #8b968f;
  --rule: #d8e0d8;
  --accent: #0f6b52;
  --accent-soft: #e2efe9;
  --pending: #8a6524;
  --pending-soft: #f4ebd9;
  --mark: #cdeadd;
  --shadow: 0 1px 2px rgba(20, 24, 26, .06);
  --serif: ui-serif, Georgia, "Iowan Old Style", "Times New Roman", serif;
  --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground: #0e1311;
    --surface: #161c19;
    --surface-2: #1d2521;
    --ink: #e7eee9;
    --muted: #93a09a;
    --faint: #6d7a74;
    --rule: #26302b;
    --accent: #56bd99;
    --accent-soft: #17302a;
    --pending: #d3a75a;
    --pending-soft: #2d2617;
    --mark: #1d4437;
    --shadow: 0 1px 2px rgba(0, 0, 0, .3);
  }
}
:root[data-theme="dark"] {
  --ground: #0e1311;
  --surface: #161c19;
  --surface-2: #1d2521;
  --ink: #e7eee9;
  --muted: #93a09a;
  --faint: #6d7a74;
  --rule: #26302b;
  --accent: #56bd99;
  --accent-soft: #17302a;
  --pending: #d3a75a;
  --pending-soft: #2d2617;
  --mark: #1d4437;
  --shadow: 0 1px 2px rgba(0, 0, 0, .3);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: var(--serif);
  font-size: 17px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 60rem; margin: 0 auto; padding: 0 1.25rem; }

.banner {
  background: var(--accent-soft);
  border-bottom: 1px solid var(--rule);
  font-family: var(--sans);
  font-size: .82rem;
  color: var(--muted);
}
.banner .wrap { display: flex; gap: .6rem; padding-top: .7rem; padding-bottom: .7rem; }
.banner strong { color: var(--accent); font-weight: 650; }

header.masthead { border-bottom: 1px solid var(--rule); background: var(--surface); }
.masthead .wrap { padding-top: 2.4rem; padding-bottom: 1.6rem; }
.eyebrow {
  font-family: var(--sans); font-size: .68rem; font-weight: 700;
  letter-spacing: .16em; text-transform: uppercase; color: var(--accent);
}
h1 {
  margin: .45rem 0 .35rem; font-size: 2.3rem; line-height: 1.08;
  letter-spacing: -.025em; text-wrap: balance;
}
.lede { margin: 0; max-width: 34rem; color: var(--muted); }

.stats { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: 1.5rem; }
.tile {
  flex: 1 1 8.5rem; padding: .7rem .85rem; background: var(--surface-2);
  border: 1px solid var(--rule); border-radius: 8px;
}
.tile .n {
  display: block; font-family: var(--sans); font-size: 1.35rem; font-weight: 680;
  letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}
.tile .k {
  font-family: var(--sans); font-size: .68rem; font-weight: 600;
  letter-spacing: .1em; text-transform: uppercase; color: var(--faint);
}

.controls { display: flex; gap: .5rem; margin: 1.75rem 0 .5rem; }
#q {
  flex: 1; padding: .62rem .85rem; font-family: var(--sans); font-size: .92rem;
  color: var(--ink); background: var(--surface); border: 1px solid var(--rule);
  border-radius: 8px;
}
#q:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
.count {
  font-family: var(--sans); font-size: .78rem; color: var(--faint);
  margin: 0 0 1.25rem;
}

.year {
  margin: 1.9rem 0 .5rem; font-family: var(--sans); font-size: .7rem;
  font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
  color: var(--faint);
}
ul.rows { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--rule); }
li.row { border-bottom: 1px solid var(--rule); }
button.row-btn {
  display: flex; gap: 1rem; align-items: baseline; width: 100%;
  padding: .8rem .3rem; font: inherit; text-align: left; color: inherit;
  background: none; border: 0; cursor: pointer;
}
button.row-btn:hover { background: var(--accent-soft); }
button.row-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.date {
  flex: none; width: 6.6rem; font-family: var(--sans); font-size: .79rem;
  color: var(--muted); font-variant-numeric: tabular-nums;
}
.title { flex: 1; font-size: 1rem; }
.chip {
  flex: none; font-family: var(--sans); font-size: .66rem; font-weight: 650;
  letter-spacing: .05em; text-transform: uppercase; padding: .16rem .5rem;
  border-radius: 999px; white-space: nowrap;
}
.chip.full { color: var(--accent); background: var(--accent-soft); }
.chip.link { color: var(--pending); background: var(--pending-soft); }

dialog {
  width: min(42rem, 92vw); max-height: 86vh; padding: 0; color: var(--ink);
  background: var(--surface); border: 1px solid var(--rule); border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0,0,0,.22);
}
dialog::backdrop { background: rgba(8, 12, 10, .55); }
.sheet { display: flex; flex-direction: column; max-height: 86vh; }
.sheet-head {
  padding: 1.3rem 1.5rem 1rem; border-bottom: 1px solid var(--rule);
  display: flex; gap: 1rem; align-items: flex-start;
}
.sheet-head h2 { margin: .3rem 0 .3rem; font-size: 1.4rem; line-height: 1.2; letter-spacing: -.02em; }
.byline { margin: 0; font-family: var(--sans); font-size: .8rem; color: var(--faint); }
.close {
  flex: none; padding: .3rem .55rem; font-family: var(--sans); font-size: 1.1rem;
  line-height: 1; color: var(--muted); background: var(--surface-2);
  border: 1px solid var(--rule); border-radius: 6px; cursor: pointer;
}
.sheet-body { padding: 1.2rem 1.5rem 1.5rem; overflow-y: auto; }
.body-text { white-space: pre-wrap; overflow-wrap: break-word; margin: 0 0 1.25rem; }
.notice {
  margin: 0 0 1.25rem; padding: .9rem 1.05rem; background: var(--pending-soft);
  border: 1px solid var(--rule); border-left: 3px solid var(--pending);
  border-radius: 8px; font-family: var(--sans); font-size: .88rem; color: var(--muted);
}
.notice b { display: block; margin-bottom: .25rem; color: var(--ink); font-weight: 650; }
.panel {
  padding: .9rem 1.05rem; background: var(--surface-2);
  border: 1px solid var(--rule); border-radius: 8px; margin-bottom: .75rem;
}
.panel h3 {
  margin: 0 0 .5rem; font-family: var(--sans); font-size: .67rem; font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase; color: var(--faint);
}
.panel ul { margin: 0; padding: 0; list-style: none; display: grid; gap: .35rem; }
.panel a { color: var(--accent); font-family: var(--sans); font-size: .88rem; }
mark { background: var(--mark); color: inherit; padding: 0 .12em; border-radius: 2px; }
.empty { padding: 3rem 0; text-align: center; color: var(--faint); }

footer {
  margin-top: 3rem; padding: 1.6rem 0 2.6rem; border-top: 1px solid var(--rule);
  font-family: var(--sans); font-size: .8rem; color: var(--faint);
}
footer p { margin: 0 0 .35rem; }
@media (max-width: 34rem) {
  h1 { font-size: 1.75rem; }
  .date { width: 100%; }
  button.row-btn { flex-wrap: wrap; gap: .25rem .75rem; }
}
</style>

<div class="banner"><div class="wrap">
  <span><strong>Preview.</strong> Real indexed data from the community, rendered as a
  standalone page. The production app reads the same records from Supabase.</span>
</div></div>

<header class="masthead"><div class="wrap">
  <span class="eyebrow">GOAT Academy</span>
  <h1>Felix&rsquo;s Notes Archive</h1>
  <p class="lede">Every weekly market note Felix has published, recovered from the
  community and indexed in one place &mdash; with each original document one click away.</p>
  <div class="stats" id="stats"></div>
</div></header>

<div class="wrap">
  <div class="controls">
    <input id="q" type="search" placeholder="Search titles and note text &mdash; gold, VIX, basis trade&hellip;"
           aria-label="Search the notes" autocomplete="off">
  </div>
  <p class="count" id="count"></p>
  <div id="list"></div>
</div>

<footer><div class="wrap">
  <p>Charts and watchlists live inside the original documents and are preserved as
  links rather than copied, so nothing is silently lost.</p>
  <p>Historical market commentary, archived for reference. Not financial advice.</p>
</div></footer>

<dialog id="sheet"><div class="sheet">
  <div class="sheet-head">
    <div>
      <span class="eyebrow" id="s-date"></span>
      <h2 id="s-title"></h2>
      <p class="byline" id="s-by"></p>
    </div>
    <button class="close" id="s-close" aria-label="Close">&times;</button>
  </div>
  <div class="sheet-body" id="s-body"></div>
</div></dialog>

<script>
const DATA = __DATA__;
const notes = DATA.notes;
const weekly = notes.filter(n => n.kind === "weekly_note");
const withBody = weekly.filter(n => n.body);

const esc = s => (s ?? "").replace(/[&<>"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

const fmt = d => d
  ? new Date(d + "T00:00:00Z").toLocaleDateString("en-GB",
      { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
  : "Undated";

function renderStats() {
  const dates = weekly.map(n => n.date).filter(Boolean).sort();
  const span = dates.length
    ? fmt(dates[0]).replace(/ \\d{4}$/, "") + " &ndash; " + fmt(dates[dates.length - 1])
    : "&mdash;";
  const tiles = [
    [weekly.length, "Weekly notes"],
    [withBody.length, "With full text"],
    [weekly.length - withBody.length, "Link only"],
    [span, "Coverage"],
  ];
  document.getElementById("stats").innerHTML = tiles.map(
    ([n, k]) => `<div class="tile"><span class="n">${n}</span><span class="k">${k}</span></div>`
  ).join("");
}

function highlight(text, q) {
  if (!q) return esc(text);
  const re = new RegExp("(" + q.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&") + ")", "ig");
  return esc(text).replace(re, "<mark>$1</mark>");
}

function renderList(q) {
  const query = q.trim().toLowerCase();
  const hits = weekly.filter(n =>
    !query ||
    n.title.toLowerCase().includes(query) ||
    (n.body && n.body.toLowerCase().includes(query)) ||
    n.postText.toLowerCase().includes(query));

  document.getElementById("count").textContent = query
    ? `${hits.length} of ${weekly.length} notes match “${q.trim()}”`
    : `${weekly.length} notes, newest first`;

  if (!hits.length) {
    document.getElementById("list").innerHTML =
      '<p class="empty">Nothing matched. Note text is only searchable for the ' +
      withBody.length + ' notes extracted so far.</p>';
    return;
  }

  const groups = new Map();
  for (const n of hits) {
    const y = n.date ? n.date.slice(0, 4) : "Undated";
    (groups.get(y) ?? groups.set(y, []).get(y)).push(n);
  }

  document.getElementById("list").innerHTML = [...groups].map(([year, rows]) => `
    <h2 class="year">${year}</h2>
    <ul class="rows">${rows.map(n => `
      <li class="row"><button class="row-btn" data-id="${esc(n.id)}">
        <span class="date">${fmt(n.date)}</span>
        <span class="title">${highlight(n.title, q.trim())}</span>
        <span class="chip ${n.body ? "full" : "link"}">${
          n.body ? n.words.toLocaleString() + " words" : "link only"}</span>
      </button></li>`).join("")}</ul>`).join("");
}

const sheet = document.getElementById("sheet");

function openNote(id) {
  const n = notes.find(x => x.id === id);
  if (!n) return;
  document.getElementById("s-date").textContent = fmt(n.date);
  document.getElementById("s-title").textContent = n.title;
  document.getElementById("s-by").textContent =
    (n.author || "Felix Prehn") + (n.words ? ` · ${n.words.toLocaleString()} words` : "");

  const links = n.links.map(l =>
    `<li><a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${
      esc(DATA.linkLabels[l.kind] || "Link")}</a></li>`).join("");

  document.getElementById("s-body").innerHTML = [
    n.body
      ? `<div class="body-text">${esc(n.body)}</div>`
      : `<div class="notice"><b>Full text not yet extracted</b>
         This note&rsquo;s body still lives in its original document. The links below open
         the source directly.</div>` +
        (n.postText ? `<div class="body-text">${esc(n.postText)}</div>` : ""),
    links ? `<div class="panel"><h3>Original sources</h3><ul>${links}</ul></div>` : "",
    n.postUrl
      ? `<div class="panel"><h3>In the community</h3><ul><li><a href="${esc(n.postUrl)}"
         target="_blank" rel="noopener noreferrer">Open the original post</a></li></ul></div>`
      : "",
  ].join("");

  document.getElementById("s-body").scrollTop = 0;
  sheet.showModal();
}

document.getElementById("list").addEventListener("click", e => {
  const btn = e.target.closest("button[data-id]");
  if (btn) openNote(btn.dataset.id);
});
document.getElementById("s-close").addEventListener("click", () => sheet.close());
sheet.addEventListener("click", e => { if (e.target === sheet) sheet.close(); });

let t;
document.getElementById("q").addEventListener("input", e => {
  clearTimeout(t);
  const v = e.target.value;
  t = setTimeout(() => renderList(v), 120);
});

renderStats();
renderList("");
</script>
"""


def main() -> int:
    payload = collect()
    html = HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)

    weekly = [n for n in payload["notes"] if n["kind"] == "weekly_note"]
    with_body = [n for n in weekly if n["body"]]
    print(f"notes:      {len(weekly)} weekly ({len(with_body)} with full text)")
    print(f"wrote       {OUT.relative_to(ROOT)}  ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
