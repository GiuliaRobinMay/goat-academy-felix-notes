-- Felix's Weekly Market Notes — core schema
--
-- The notes were never stored in the community itself: each weekly post in
-- Mighty Networks space 19161480 is a wrapper linking out to a Google Doc, a
-- goatacademy.org article, or (a few weeks) carrying the text inline. This
-- schema therefore separates three things:
--
--   1. the note record itself, which we can populate from the community index
--      alone (title, date, permalink) before any body text has been extracted;
--   2. the body text, which arrives later and is nullable until it does;
--   3. the outbound links, kept verbatim so charts, watchlists and the
--      Heartbeat Scanner stay one click away rather than being lost.
--
-- Every load is keyed on the Mighty post id so the pipeline can be re-run
-- idempotently as new notes are published.

create extension if not exists "pgcrypto";
create extension if not exists "vector";

-- ---------------------------------------------------------------------------
-- notes
-- ---------------------------------------------------------------------------

create type note_kind as enum ('weekly_note', 'announcement');

-- Where the body text lives upstream. 'unknown' exists so an unrecognised
-- future format still loads rather than failing the whole run.
create type note_source_type as enum ('google_doc', 'article', 'inline', 'video', 'unknown');

create type extraction_status as enum ('pending', 'extracted', 'unavailable');

create table notes (
    id                uuid primary key default gen_random_uuid(),

    -- Mighty Networks resourceId. Stable across edits and re-runs, so this is
    -- the natural key the loader upserts on.
    post_id           text not null unique,

    title             text not null,
    -- Null only for announcements, which have no date in their title.
    note_date         date,
    kind              note_kind not null default 'weekly_note',
    source_type       note_source_type not null default 'unknown',

    author            text,
    post_url          text,
    published_at      timestamptz,
    comment_count     integer not null default 0,

    -- Text of the community post itself. For most weeks this is just the link
    -- wrapper, but for inline weeks it is the entire note.
    post_text         text,

    -- Full note body, extracted from the upstream source. Null until the
    -- extraction pass has run for this note.
    body_md           text,
    body_source_url   text,
    body_word_count   integer,

    extraction_status extraction_status not null default 'pending',
    extracted_at      timestamptz,

    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);

comment on column notes.post_id is
    'Mighty Networks resourceId — natural key for idempotent re-loads.';
comment on column notes.body_md is
    'Full note text; null until extracted. Charts are not captured here — see note_links.';

create index notes_note_date_idx on notes (note_date desc nulls last);
create index notes_kind_idx on notes (kind);
create index notes_extraction_status_idx on notes (extraction_status);

-- ---------------------------------------------------------------------------
-- full-text search
-- ---------------------------------------------------------------------------

-- Title is weighted above body so a search for a date or topic surfaces the
-- note named for it ahead of notes that merely mention it in passing.
alter table notes add column search_tsv tsvector
    generated always as (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(post_text, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(body_md, '')), 'C')
    ) stored;

create index notes_search_idx on notes using gin (search_tsv);

-- ---------------------------------------------------------------------------
-- note_links
-- ---------------------------------------------------------------------------

-- Charts live inside the source documents as images and do not survive text
-- extraction. Rather than lose them, every outbound link is preserved so the
-- app can always link back to the original.
create type note_link_kind as enum (
    'source_doc',       -- the Google Doc the note body came from
    'watchlist_sheet',  -- Felix's watchlist spreadsheet for that week
    'article',          -- goatacademy.org article (Jul 2026 onward)
    'heartbeat',        -- app.goatacademy.org Heartbeat Scanner
    'video',            -- Mighty-hosted video
    'other'
);

create table note_links (
    id         uuid primary key default gen_random_uuid(),
    note_id    uuid not null references notes (id) on delete cascade,
    kind       note_link_kind not null,
    url        text not null,
    label      text,
    created_at timestamptz not null default now(),

    unique (note_id, kind, url)
);

create index note_links_note_id_idx on note_links (note_id);

-- ---------------------------------------------------------------------------
-- note_chunks — semantic search
-- ---------------------------------------------------------------------------

-- Notes run long and cover several themes each, so embedding a whole note
-- blurs it. Chunking keeps "what did Felix say about gold last October?"
-- answerable at passage level.
create table note_chunks (
    id          uuid primary key default gen_random_uuid(),
    note_id     uuid not null references notes (id) on delete cascade,
    chunk_index integer not null,
    heading     text,
    content     text not null,
    embedding   vector(1536),
    created_at  timestamptz not null default now(),

    unique (note_id, chunk_index)
);

create index note_chunks_note_id_idx on note_chunks (note_id);

-- IVFFlat needs data present before it can be tuned; it is created in a later
-- migration once the corpus is loaded. Until then chunk search falls back to a
-- sequential scan, which is fine at ~71 notes.

-- ---------------------------------------------------------------------------
-- updated_at maintenance
-- ---------------------------------------------------------------------------

create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger notes_set_updated_at
    before update on notes
    for each row
    execute function set_updated_at();

-- ---------------------------------------------------------------------------
-- row level security
-- ---------------------------------------------------------------------------

-- The archive is member-facing content: readable by any authenticated member,
-- writable only by the service role that runs the pipeline.
alter table notes enable row level security;
alter table note_links enable row level security;
alter table note_chunks enable row level security;

create policy notes_read on notes
    for select to authenticated using (true);

create policy note_links_read on note_links
    for select to authenticated using (true);

create policy note_chunks_read on note_chunks
    for select to authenticated using (true);
