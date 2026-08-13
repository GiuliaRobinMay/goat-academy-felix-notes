#!/usr/bin/env python3
"""Build a normalised index of Felix's Weekly Market Notes from raw Mighty Networks search pages.

Reads the paginated search dumps in data/raw/pages/*.json, dedupes by post id,
parses the note date out of the post title, and extracts every outbound link
(Google Doc, Google Sheet, goatacademy.org article, Heartbeat Scanner, video).

Output: data/notes_index.json
"""

import json
import pathlib
import re
import sys
from datetime import date, timedelta

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ROOT / "data" / "raw" / "pages"
OUT = ROOT / "data" / "notes_index.json"

SPACE_ID = "19161480"

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

# "Felix's notes for 8 August 2026", "Felix' notes for 05 May 2025 - Weekly", ...
DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})")

DOC_RE = re.compile(r"docs\.google\.com/document/d/([A-Za-z0-9_-]+)")
SHEET_RE = re.compile(r"docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)")
ARTICLE_RE = re.compile(r"https?://(?:www\.)?goatacademy\.org/[^\s\"'<>]+")
HEARTBEAT_RE = re.compile(r"https?://app\.goatacademy\.org/[^\s\"'<>]+")
VIDEO_RE = re.compile(r"https?://video\.mn\.co/[^\s\"'<>]+")

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"[ \t\r\f\v]+")


def strip_html(html: str) -> str:
    """Turn a Mighty post body into readable plain text."""
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = TAG_RE.sub("", text)
    text = (
        text.replace("&nbsp;", " ").replace("&amp;", "&")
        .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    text = WS_RE.sub(" ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def parse_note_date(title: str):
    m = DATE_RE.search(title or "")
    if not m:
        return None
    day, month_word, year = m.group(1), m.group(2).lower(), m.group(3)
    month = MONTHS.get(month_word)
    if not month:
        return None
    try:
        return date(int(year), month, int(day)).isoformat()
    except ValueError:
        return None


def uniq(seq):
    seen, out = set(), []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def main() -> int:
    if not PAGES.exists():
        print(f"no raw pages at {PAGES}", file=sys.stderr)
        return 1

    by_id = {}
    for path in sorted(PAGES.glob("*.json")):
        payload = json.loads(path.read_text())
        for edge in payload.get("edges", []):
            node = edge.get("node") or {}
            if node.get("__typename") != "Post":
                continue
            if (node.get("space") or {}).get("resourceId") != SPACE_ID:
                continue
            by_id[node["resourceId"]] = node

    notes, modules = [], []
    for rid, node in by_id.items():
        title = node.get("title") or ""
        body = node.get("body") or ""

        # Quarterly divider posts ("➽ Felix Notes | Q4 2025") organise the space
        # but carry no content of their own.
        if title.strip().startswith("➽"):
            modules.append({"post_id": rid, "title": title.strip(), "url": node.get("url")})
            continue

        doc_ids = uniq(DOC_RE.findall(body))
        record = {
            "post_id": rid,
            "title": title.strip(),
            "note_date": parse_note_date(title),
            "post_url": node.get("url"),
            "published_at": node.get("publishedAt"),
            "author": (node.get("creator") or {}).get("name"),
            "comment_count": node.get("commentCount", 0),
            "post_text": strip_html(body),
            "doc_ids": doc_ids,
            "doc_urls": [f"https://docs.google.com/document/d/{d}/edit" for d in doc_ids],
            "sheet_ids": uniq(SHEET_RE.findall(body)),
            "article_urls": uniq(ARTICLE_RE.findall(body)),
            "heartbeat_urls": uniq(HEARTBEAT_RE.findall(body)),
            "video_urls": uniq(VIDEO_RE.findall(body)),
        }

        if doc_ids:
            record["source_type"] = "google_doc"
        elif record["article_urls"]:
            record["source_type"] = "article"
        elif len(record["post_text"]) > 400:
            # A handful of weeks Felix wrote the whole note straight into the
            # post body instead of linking out (e.g. "Quick notes for 14 Oct 2025").
            record["source_type"] = "inline"
        elif record["video_urls"]:
            record["source_type"] = "video"
        else:
            record["source_type"] = "unknown"

        # Undated posts in this space are promos/announcements, not weekly notes.
        record["kind"] = "weekly_note" if record["note_date"] else "announcement"

        notes.append(record)

    notes.sort(key=lambda n: (n["note_date"] or "", n["title"]))

    dated = [n for n in notes if n["note_date"]]
    undated = [n for n in notes if not n["note_date"]]

    # Notes land on varying weekdays, so fixed Mon-Sun windows produce false
    # positives. Measure the actual span between consecutive notes instead: a
    # gap of more than 10 days means a week genuinely has no note.
    gaps = []
    if dated:
        dates = sorted({date.fromisoformat(n["note_date"]) for n in dated})
        for prev, nxt in zip(dates, dates[1:]):
            if (nxt - prev).days > 10:
                gaps.append({
                    "after": prev.isoformat(),
                    "before": nxt.isoformat(),
                    "days": (nxt - prev).days,
                })

    by_source = {}
    for n in notes:
        if n["kind"] != "weekly_note":
            continue
        by_source[n["source_type"]] = by_source.get(n["source_type"], 0) + 1

    index = {
        "space_id": SPACE_ID,
        "space_title": "Felix's Weekly Market Notes",
        "note_count": len(notes),
        "module_count": len(modules),
        "date_range": [dated[0]["note_date"], dated[-1]["note_date"]] if dated else None,
        "undated_count": len(undated),
        "by_source_type": by_source,
        "skipped_weeks": gaps,
        "modules": sorted(modules, key=lambda m: m["title"]),
        "notes": notes,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(index, indent=2, ensure_ascii=False))

    print(f"notes:        {len(notes)}")
    print(f"modules:      {len(modules)}")
    print(f"date range:   {index['date_range']}")
    print(f"undated:      {len(undated)}")
    print(f"by source:    {by_source}")
    print(f"skipped wks:  {len(gaps)} -> " + ", ".join(f"{g['after']}..{g['before']}" for g in gaps))
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
