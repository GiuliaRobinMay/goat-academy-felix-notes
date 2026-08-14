#!/usr/bin/env python3
"""Load the notes index (and any extracted bodies) into Supabase.

Safe to run repeatedly: every row is upserted on the Mighty post id, so a
re-run after a new note is published, or after more bodies have been
extracted, updates in place rather than duplicating.

Usage:
    export DATABASE_URL='postgresql://postgres:...@db.<ref>.supabase.co:5432/postgres'
    python3 scripts/load_supabase.py [--dry-run]
"""

import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "notes_index.json"
DOCS = ROOT / "data" / "raw" / "docs"

# Index source_type values map 1:1 onto the note_source_type enum, but guard
# against an unrecognised value rather than failing the whole load.
KNOWN_SOURCE_TYPES = {"google_doc", "article", "inline", "video", "unknown"}

UPSERT_NOTE = """
insert into notes (
    post_id, title, note_date, kind, source_type, author, post_url,
    published_at, comment_count, post_text, body_md, body_source_url,
    body_word_count, extraction_status, extracted_at
) values (
    %(post_id)s, %(title)s, %(note_date)s, %(kind)s, %(source_type)s,
    %(author)s, %(post_url)s, %(published_at)s, %(comment_count)s,
    %(post_text)s, %(body_md)s, %(body_source_url)s, %(body_word_count)s,
    -- Cast both uses explicitly: the same placeholder appears as an enum here
    -- and in a text comparison below, which Postgres cannot type on its own.
    %(extraction_status)s::extraction_status,
    case when %(extraction_status)s::text = 'extracted' then now() else null end
)
on conflict (post_id) do update set
    title             = excluded.title,
    note_date         = excluded.note_date,
    kind              = excluded.kind,
    source_type       = excluded.source_type,
    author            = excluded.author,
    post_url          = excluded.post_url,
    published_at      = excluded.published_at,
    comment_count     = excluded.comment_count,
    post_text         = excluded.post_text,
    -- Never overwrite an extracted body with a null from an index-only re-run.
    body_md           = coalesce(excluded.body_md, notes.body_md),
    body_source_url   = coalesce(excluded.body_source_url, notes.body_source_url),
    body_word_count   = coalesce(excluded.body_word_count, notes.body_word_count),
    extraction_status = case
        when excluded.extraction_status = 'extracted' then 'extracted'::extraction_status
        else notes.extraction_status
    end,
    extracted_at      = case
        when excluded.extraction_status = 'extracted' and notes.extracted_at is null
            then now()
        else notes.extracted_at
    end
returning id;
"""

UPSERT_LINK = """
insert into note_links (note_id, kind, url, label)
values (%(note_id)s, %(kind)s, %(url)s, %(label)s)
on conflict (note_id, kind, url) do nothing;
"""


def link_rows(note: dict) -> list[tuple[str, str, str | None]]:
    """Every outbound link on a note, as (kind, url, label)."""
    rows: list[tuple[str, str, str | None]] = []
    for url in note.get("doc_urls", []):
        rows.append(("source_doc", url, "Source document (includes charts)"))
    for sheet_id in note.get("sheet_ids", []):
        rows.append((
            "watchlist_sheet",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
            "Watchlist",
        ))
    for url in note.get("article_urls", []):
        rows.append(("article", url, "Felix's Notes article"))
    for url in note.get("heartbeat_urls", []):
        rows.append(("heartbeat", url, "Heartbeat Scanner"))
    for url in note.get("video_urls", []):
        rows.append(("video", url, "Video"))
    return rows


def load_body(note: dict) -> tuple[str | None, str | None]:
    """Return (body_md, body_source_url) if a body has been extracted."""
    for doc_id in note.get("doc_ids", []):
        path = DOCS / f"{doc_id}.md"
        if path.exists():
            text = path.read_text().strip()
            if text:
                return text, f"https://docs.google.com/document/d/{doc_id}/edit"

    # Inline weeks carry the whole note in the community post itself.
    if note.get("source_type") == "inline" and note.get("post_text"):
        return note["post_text"], note.get("post_url")

    return None, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be loaded without connecting to the database",
    )
    args = parser.parse_args()

    if not INDEX.exists():
        print(f"missing {INDEX.relative_to(ROOT)} — run scripts/build_index.py first",
              file=sys.stderr)
        return 1

    index = json.loads(INDEX.read_text())
    notes = index["notes"]

    prepared = []
    for note in notes:
        body_md, body_source_url = load_body(note)
        source_type = note.get("source_type", "unknown")
        if source_type not in KNOWN_SOURCE_TYPES:
            source_type = "unknown"

        prepared.append({
            "row": {
                "post_id": note["post_id"],
                "title": note["title"],
                "note_date": note.get("note_date"),
                "kind": note.get("kind", "weekly_note"),
                "source_type": source_type,
                "author": note.get("author"),
                "post_url": note.get("post_url"),
                "published_at": note.get("published_at"),
                "comment_count": note.get("comment_count", 0),
                "post_text": note.get("post_text"),
                "body_md": body_md,
                "body_source_url": body_source_url,
                "body_word_count": len(body_md.split()) if body_md else None,
                "extraction_status": "extracted" if body_md else "pending",
            },
            "links": link_rows(note),
        })

    with_body = sum(1 for p in prepared if p["row"]["body_md"])
    total_links = sum(len(p["links"]) for p in prepared)

    print(f"notes to load:   {len(prepared)}")
    print(f"  with body:     {with_body}")
    print(f"  pending body:  {len(prepared) - with_body}")
    print(f"links to load:   {total_links}")

    if args.dry_run:
        print("\ndry run — nothing written")
        return 0

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("\nDATABASE_URL is not set. Export your Supabase connection string:\n"
              "  export DATABASE_URL='postgresql://postgres:...@db.<ref>.supabase.co:5432/postgres'",
              file=sys.stderr)
        return 2

    try:
        import psycopg
    except ImportError:
        print("psycopg is not installed — pip install -r scripts/requirements.txt",
              file=sys.stderr)
        return 2

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for item in prepared:
                cur.execute(UPSERT_NOTE, item["row"])
                note_id = cur.fetchone()[0]
                for kind, url, label in item["links"]:
                    cur.execute(UPSERT_LINK, {
                        "note_id": note_id,
                        "kind": kind,
                        "url": url,
                        "label": label,
                    })
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("select * from archive_stats();")
            stats = cur.fetchone()

    print(f"\nloaded. archive now: {stats[0]} notes "
          f"({stats[2]} extracted, {stats[3]} pending), {stats[5]} .. {stats[6]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
