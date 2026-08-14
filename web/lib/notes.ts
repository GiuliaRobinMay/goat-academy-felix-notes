import { createClient } from "@supabase/supabase-js";

export type NoteKind = "weekly_note" | "announcement";
export type ExtractionStatus = "pending" | "extracted" | "unavailable";
export type NoteLinkKind =
  | "source_doc"
  | "watchlist_sheet"
  | "article"
  | "heartbeat"
  | "video"
  | "other";

export interface NoteLink {
  kind: NoteLinkKind;
  url: string;
  label: string | null;
}

export interface Note {
  id: string;
  post_id: string;
  title: string;
  note_date: string | null;
  kind: NoteKind;
  author: string | null;
  post_url: string | null;
  post_text: string | null;
  body_md: string | null;
  body_source_url: string | null;
  body_word_count: number | null;
  extraction_status: ExtractionStatus;
  note_links?: NoteLink[];
}

export interface ArchiveStats {
  total_notes: number;
  weekly_notes: number;
  extracted: number;
  pending: number;
  unavailable: number;
  earliest_note: string | null;
  latest_note: string | null;
}

export interface SearchHit {
  id: string;
  post_id: string;
  title: string;
  note_date: string | null;
  post_url: string | null;
  snippet: string | null;
  rank: number;
}

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

/**
 * Null when Supabase isn't configured yet, so the app renders a setup notice
 * instead of crashing. The archive is loaded by the Python pipeline, which can
 * run long after the app is first deployed.
 */
export const supabase =
  url && anonKey ? createClient(url, anonKey, { auth: { persistSession: false } }) : null;

export const isConfigured = supabase !== null;

const LINK_LABELS: Record<NoteLinkKind, string> = {
  source_doc: "Original document",
  watchlist_sheet: "Watchlist",
  article: "Full article",
  heartbeat: "Heartbeat Scanner",
  video: "Video",
  other: "Link",
};

export function linkLabel(link: NoteLink): string {
  return link.label ?? LINK_LABELS[link.kind] ?? "Link";
}

export function formatNoteDate(value: string | null): string {
  if (!value) return "Undated";
  // Parse as UTC so a note dated the 7th never renders as the 6th.
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export async function getArchiveStats(): Promise<ArchiveStats | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.rpc("archive_stats").single();
  if (error) throw new Error(`archive_stats failed: ${error.message}`);
  return data as ArchiveStats;
}

export async function listNotes(limit = 200): Promise<Note[]> {
  if (!supabase) return [];
  const { data, error } = await supabase
    .from("notes")
    .select(
      "id, post_id, title, note_date, kind, author, post_url, post_text, " +
        "body_word_count, extraction_status, body_md, body_source_url"
    )
    .eq("kind", "weekly_note")
    .order("note_date", { ascending: false, nullsFirst: false })
    .limit(limit);

  if (error) throw new Error(`listNotes failed: ${error.message}`);
  // Cast through unknown: without generated database types supabase-js cannot
  // infer a row shape from the select string. Run `supabase gen types
  // typescript` and swap these for the generated types when convenient.
  return (data ?? []) as unknown as Note[];
}

export async function getNote(postId: string): Promise<Note | null> {
  if (!supabase) return null;
  const { data, error } = await supabase
    .from("notes")
    .select("*, note_links(kind, url, label)")
    .eq("post_id", postId)
    .maybeSingle();

  if (error) throw new Error(`getNote failed: ${error.message}`);
  return (data as unknown as Note) ?? null;
}

export async function searchNotes(query: string, limit = 30): Promise<SearchHit[]> {
  if (!supabase || !query.trim()) return [];
  const { data, error } = await supabase.rpc("search_notes", {
    query,
    max_results: limit,
  });
  if (error) throw new Error(`search_notes failed: ${error.message}`);
  return (data ?? []) as SearchHit[];
}
