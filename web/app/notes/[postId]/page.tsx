import Link from "next/link";
import { notFound } from "next/navigation";
import { formatNoteDate, getNote, isConfigured, linkLabel } from "@/lib/notes";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: { postId: string } }) {
  if (!isConfigured) return { title: "Felix's Notes Archive" };
  const note = await getNote(params.postId);
  return { title: note ? `${note.title} | Felix's Notes` : "Note not found" };
}

export default async function NotePage({ params }: { params: { postId: string } }) {
  if (!isConfigured) notFound();

  const note = await getNote(params.postId);
  if (!note) notFound();

  const links = note.note_links ?? [];
  // The source doc is where the charts live, so it leads the list.
  const ordered = [...links].sort((a, b) =>
    a.kind === "source_doc" ? -1 : b.kind === "source_doc" ? 1 : 0
  );

  const body = note.body_md?.trim();

  return (
    <article>
      <Link href="/" className="back-link">
        &larr; All notes
      </Link>

      <header className="note-header">
        <span className="eyebrow">{formatNoteDate(note.note_date)}</span>
        <h1>{note.title}</h1>
        <p className="byline">
          {note.author ?? "Felix Prehn"}
          {note.body_word_count ? ` · ${note.body_word_count.toLocaleString()} words` : null}
        </p>
      </header>

      {body ? (
        <div className="note-body">{body}</div>
      ) : (
        <div className="notice">
          <h2>Full text not yet extracted</h2>
          <p>
            This note&rsquo;s body still lives in its original document. The links below
            open the source directly.
          </p>
          {note.post_text ? <p>{note.post_text}</p> : null}
        </div>
      )}

      {ordered.length > 0 ? (
        <div className="panel">
          <h2>Original sources</h2>
          <ul>
            {ordered.map((link) => (
              <li key={`${link.kind}-${link.url}`}>
                <a href={link.url} target="_blank" rel="noopener noreferrer">
                  {linkLabel(link)}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {note.post_url ? (
        <div className="panel">
          <h2>In the community</h2>
          <p>
            <a href={note.post_url} target="_blank" rel="noopener noreferrer">
              Open the original post
            </a>{" "}
            to read the discussion.
          </p>
        </div>
      ) : null}
    </article>
  );
}
