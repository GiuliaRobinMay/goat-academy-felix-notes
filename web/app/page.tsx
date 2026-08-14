import Link from "next/link";
import {
  formatNoteDate,
  getArchiveStats,
  isConfigured,
  listNotes,
  searchNotes,
  type Note,
} from "@/lib/notes";

export const dynamic = "force-dynamic";

function SetupNotice() {
  return (
    <div className="notice">
      <h2>Connect the archive</h2>
      <p>
        The app is running but no Supabase project is configured yet. Copy{" "}
        <code>.env.example</code> to <code>.env.local</code> and fill in your project
        URL and anon key, then run the migrations and the loader:
      </p>
      <pre>{`psql "$DATABASE_URL" -f supabase/migrations/0001_init.sql
psql "$DATABASE_URL" -f supabase/migrations/0002_search.sql
python3 scripts/load_supabase.py`}</pre>
    </div>
  );
}

function groupByYear(notes: Note[]): [string, Note[]][] {
  const groups = new Map<string, Note[]>();
  for (const note of notes) {
    const year = note.note_date ? note.note_date.slice(0, 4) : "Undated";
    const bucket = groups.get(year);
    if (bucket) bucket.push(note);
    else groups.set(year, [note]);
  }
  // Notes arrive newest-first, so insertion order is already correct.
  return [...groups.entries()];
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: { q?: string };
}) {
  if (!isConfigured) {
    return (
      <>
        <section className="intro">
          <h1>Felix&rsquo;s Notes Archive</h1>
          <p>Every weekly market note, in one searchable place.</p>
        </section>
        <SetupNotice />
      </>
    );
  }

  const query = searchParams.q?.trim() ?? "";
  const [stats, notes, hits] = await Promise.all([
    getArchiveStats(),
    query ? Promise.resolve([]) : listNotes(),
    query ? searchNotes(query) : Promise.resolve([]),
  ]);

  const coverage =
    stats && stats.earliest_note && stats.latest_note
      ? `${stats.weekly_notes} weekly notes, ${formatNoteDate(
          stats.earliest_note
        )} – ${formatNoteDate(stats.latest_note)}`
      : "The archive is empty — run the loader to populate it.";

  return (
    <>
      <section className="intro">
        <h1>Felix&rsquo;s Notes Archive</h1>
        <p>{coverage}</p>

        <form className="search-form" action="/" method="get">
          <input
            type="search"
            name="q"
            defaultValue={query}
            placeholder="Search the notes — gold, VIX, breakout, rotation…"
            aria-label="Search Felix's notes"
          />
          <button type="submit">Search</button>
        </form>
      </section>

      {query ? (
        <>
          <p className="year-heading">
            {hits.length} result{hits.length === 1 ? "" : "s"} for &ldquo;{query}&rdquo;
          </p>
          {hits.length === 0 ? (
            <p className="empty">
              Nothing matched. Try a broader term, or{" "}
              <Link href="/">browse the full archive</Link>.
            </p>
          ) : (
            <ul className="note-list">
              {hits.map((hit) => (
                <li key={hit.id} className="note-row">
                  <Link href={`/notes/${hit.post_id}`}>
                    <span className="note-date">{formatNoteDate(hit.note_date)}</span>
                    <span className="note-title">
                      {hit.title}
                      {hit.snippet ? (
                        <span
                          className="snippet"
                          // Snippet comes from ts_headline, which emits only <mark> tags.
                          dangerouslySetInnerHTML={{ __html: hit.snippet }}
                        />
                      ) : null}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : notes.length === 0 ? (
        <p className="empty">
          No notes loaded yet. Run <code>python3 scripts/load_supabase.py</code>.
        </p>
      ) : (
        groupByYear(notes).map(([year, yearNotes]) => (
          <section key={year}>
            <h2 className="year-heading">{year}</h2>
            <ul className="note-list">
              {yearNotes.map((note) => (
                <li key={note.id} className="note-row">
                  <Link href={`/notes/${note.post_id}`}>
                    <span className="note-date">{formatNoteDate(note.note_date)}</span>
                    <span className="note-title">{note.title}</span>
                    <span className="note-meta">
                      {note.extraction_status === "extracted" && note.body_word_count
                        ? `${note.body_word_count.toLocaleString()} words`
                        : "link only"}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </>
  );
}
