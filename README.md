# Felix's Notes Archive

A searchable archive of Felix Prehn's weekly market notes for GOAT Academy.

## Why this exists

The notes were never really stored in the community. Each weekly entry in the
Mighty Networks space **Felix's Weekly Market Notes** (`19161480`) is a wrapper
post containing a link — the actual commentary lives somewhere else, and where
that "somewhere else" is has changed three times:

| Period | Where the note body lives |
| --- | --- |
| Apr 2025 – Jun 2026 | A Google Doc, one per week |
| Jul 2026 onward | A `goatacademy.org` article plus a Heartbeat Scanner page |
| A few scattered weeks | Inline in the community post, or a video with no text |

Those Google Docs are owned by individual personal accounts (`yenny@`,
`natalie@goatacademy.org` and others) under inconsistent names like
"Jan 11, 2026 WEEKLY". Searching Drive for "Felix" finds almost none of them.
If one of those accounts is deprovisioned, the notes it owns go with it. There
is currently no canonical archive — which is the reason this project exists.

## What has been established

Enumerated and verified from the community:

- **71 weekly notes**, spanning **7 April 2025 → 8 August 2026**
- 3 promotional posts in the same space, classified separately as announcements
- 3 quarterly module dividers (`Q4 2025`, `Q1 2026`, `Q2 2026`)

Completeness was checked by measuring the gap between consecutive notes rather
than by trusting the search ranking. Over a 488-day span where ~70 weekly notes
are expected, there are exactly **four** one-week gaps, each landing on a US
holiday week (Thanksgiving, Christmas/New Year, Memorial Day, 4 July). Those
were spot-checked against the community and are genuine skips, not misses.

## Architecture

```
data/
  notes_index.json        normalised index of every note (the pipeline's source of truth)
  raw/pages/*.json        verbatim community search responses, kept as provenance
  raw/docs/*.md           extracted note bodies, one file per Google Doc
scripts/
  build_index.py          raw search dumps  -> data/notes_index.json
  extract_docs.py         Google Docs       -> data/raw/docs/*.md
  load_supabase.py        index + bodies    -> Supabase
supabase/migrations/      schema and search functions
web/                      Next.js reader app
```

The design point worth knowing: **a note record does not depend on its body
text.** The index alone gives every note a title, date, permalink and source
links, so the archive is usable before extraction has run. `body_md` is nullable
and `extraction_status` tracks progress, so bodies can be backfilled later
without touching anything else.

### Charts

Charts are images embedded in the source documents and do not survive text
extraction. Rather than silently drop them, every outbound link is preserved in
`note_links` — the source doc, the watchlist spreadsheet, the Heartbeat Scanner,
the video. The app surfaces these on each note, so the original is always one
click away.

## Setup

### 1. Database

```bash
export DATABASE_URL='postgresql://postgres:...@db.<project-ref>.supabase.co:5432/postgres'
psql "$DATABASE_URL" -f supabase/migrations/0001_init.sql
psql "$DATABASE_URL" -f supabase/migrations/0002_search.sql
```

Requires the `vector` extension, which Supabase provides.

### 2. Load what we already have

```bash
pip install -r scripts/requirements.txt
python3 scripts/load_supabase.py --dry-run   # inspect first
python3 scripts/load_supabase.py
```

Every row upserts on the Mighty post id, so this is safe to re-run — after new
notes are published, or after more bodies have been extracted.

### 3. Extract the note bodies

This is the step that still needs credentials. Grant read access one of two
ways, then run the extractor:

```bash
# Service account — best for scheduled runs.
# Share the notes folder with the service account's client_email, read-only.
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# ...or user OAuth — best for a one-off backfill from a laptop.
export GOOGLE_OAUTH_CLIENT_SECRETS=/path/to/client_secret.json

python3 scripts/extract_docs.py --list      # what's outstanding
python3 scripts/extract_docs.py
python3 scripts/load_supabase.py            # re-run to attach the bodies
```

The extractor exports each doc verbatim through the Drive API, so bodies are
byte-for-byte what Felix wrote.

### 4. Web app

```bash
cd web
cp .env.example .env.local    # add your Supabase URL and anon key
npm install
npm run dev
```

Without Supabase configured the app still runs and shows a setup notice rather
than failing.

## Rebuilding the index

`data/notes_index.json` is generated from the raw search dumps:

```bash
python3 scripts/build_index.py
```

To pick up newly published notes, add fresh community search responses to
`data/raw/pages/` and re-run. The builder dedupes by post id, so overlapping
dumps are harmless.

## Status

| Piece | State |
| --- | --- |
| Enumeration of all 71 notes | Done and verified |
| Schema and search functions | Applied and exercised against Postgres 16 + pgvector |
| Loader | Verified end-to-end, including idempotent re-runs |
| Note bodies | **9 of 74 loaded** — the rest needs Google credentials |
| Web app | Builds and renders; not yet run against a populated database |
| Semantic search | Schema and RPC in place; needs an embedding pass once bodies land |

### Known gaps

- **Bodies are the outstanding work.** 64 Google Docs are pending. They cannot
  be fetched from this environment because `docs.google.com` and
  `goatacademy.org` are both blocked by the network egress proxy, so the
  extractor needs to run somewhere with network access and credentials.
- **The app has not been tested against real data.** It has been verified to
  build, typecheck and render, and the SQL layer was exercised directly, but the
  two have not yet been run together against a populated Supabase project.
- **Semantic search is unpopulated.** `note_chunks` and `match_note_chunks`
  exist, but nothing chunks or embeds the notes yet — that belongs after the
  bodies land, so the chunker can split on real headings.
- **Compliance.** A July 2026 note records that stop-loss columns were removed
  on compliance advice. Republishing historical market calls in a member-facing
  app deserves a review before launch.

## Scope

v1 covers **Felix's Weekly Market Notes** only. The community holds four other
Felix archives — `Felix Notes - FFA`, `Felix Notes - SPX`, `Felix' WSP Notes`
and `Felix's TrendMonster Trades` — which are not enumerated here.
