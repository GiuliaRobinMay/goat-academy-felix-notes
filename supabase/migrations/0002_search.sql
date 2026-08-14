-- Search entry points for the notes archive.
--
-- Two complementary modes: keyword search over the notes themselves, and
-- semantic search over chunks for questions phrased in natural language
-- ("what was Felix saying about gold last October?").

-- ---------------------------------------------------------------------------
-- keyword search
-- ---------------------------------------------------------------------------

create or replace function search_notes(
    query        text,
    max_results  integer default 20,
    from_date    date default null,
    to_date      date default null
)
returns table (
    id         uuid,
    post_id    text,
    title      text,
    note_date  date,
    post_url   text,
    snippet    text,
    rank       real
)
language sql
stable
as $$
    select
        n.id,
        n.post_id,
        n.title,
        n.note_date,
        n.post_url,
        ts_headline(
            'english',
            coalesce(nullif(n.body_md, ''), n.post_text, ''),
            websearch_to_tsquery('english', query),
            'MaxFragments=2, MinWords=12, MaxWords=32, StartSel=<mark>, StopSel=</mark>'
        ) as snippet,
        ts_rank(n.search_tsv, websearch_to_tsquery('english', query)) as rank
    from notes n
    where n.search_tsv @@ websearch_to_tsquery('english', query)
      and (from_date is null or n.note_date >= from_date)
      and (to_date   is null or n.note_date <= to_date)
    order by rank desc, n.note_date desc nulls last
    limit greatest(1, least(max_results, 100));
$$;

comment on function search_notes is
    'Keyword search across note titles and bodies, returning a highlighted snippet.';

-- ---------------------------------------------------------------------------
-- semantic search
-- ---------------------------------------------------------------------------

-- Caller supplies the query embedding; the app owns the embedding model so it
-- can be swapped without a migration. Distance is cosine, so similarity is
-- 1 - distance and the threshold reads the intuitive way round.
create or replace function match_note_chunks(
    query_embedding vector(1536),
    match_threshold real default 0.0,
    match_count     integer default 10
)
returns table (
    chunk_id   uuid,
    note_id    uuid,
    title      text,
    note_date  date,
    post_url   text,
    heading    text,
    content    text,
    similarity real
)
language sql
stable
as $$
    select
        c.id,
        n.id,
        n.title,
        n.note_date,
        n.post_url,
        c.heading,
        c.content,
        (1 - (c.embedding <=> query_embedding))::real as similarity
    from note_chunks c
    join notes n on n.id = c.note_id
    where c.embedding is not null
      and (1 - (c.embedding <=> query_embedding)) >= match_threshold
    order by c.embedding <=> query_embedding
    limit greatest(1, least(match_count, 100));
$$;

comment on function match_note_chunks is
    'Semantic search over note chunks. Caller passes a query embedding; returns cosine similarity.';

-- ---------------------------------------------------------------------------
-- archive coverage
-- ---------------------------------------------------------------------------

-- Backs the app's coverage indicator and gives the pipeline a cheap way to
-- report what still needs extracting.
create or replace function archive_stats()
returns table (
    total_notes      bigint,
    weekly_notes     bigint,
    extracted        bigint,
    pending          bigint,
    unavailable      bigint,
    earliest_note    date,
    latest_note      date
)
language sql
stable
as $$
    select
        count(*),
        count(*) filter (where kind = 'weekly_note'),
        count(*) filter (where extraction_status = 'extracted'),
        count(*) filter (where extraction_status = 'pending'),
        count(*) filter (where extraction_status = 'unavailable'),
        min(note_date),
        max(note_date)
    from notes;
$$;
