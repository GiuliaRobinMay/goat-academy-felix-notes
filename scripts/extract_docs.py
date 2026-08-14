#!/usr/bin/env python3
"""Fetch the Google Doc body for every note that still needs one.

This is the step that turns an index-level archive into a full-text one. It
exports each doc verbatim through the Drive API rather than copying text by
hand, so the bodies are byte-for-byte what Felix wrote.

Charts are images inside the docs and do not survive text export. That is by
design: the source doc URL is preserved on every note (see note_links), so the
app always links back to the original rather than pretending the charts exist.

Credentials — either works:

  Service account (best for scheduled runs):
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
    ...and share the notes folder (or each doc) with the service account's
    client_email, read-only.

  User OAuth (best for a one-off backfill from a laptop):
    export GOOGLE_OAUTH_CLIENT_SECRETS=/path/to/client_secret.json
    A browser window opens once; the token is cached in .google-token.json.

Usage:
    python3 scripts/extract_docs.py [--limit N] [--force] [--list]
"""

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "notes_index.json"
DOCS = ROOT / "data" / "raw" / "docs"
TOKEN_CACHE = ROOT / ".google-token.json"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Docs export cleanly to Markdown, which keeps headings and lists that the
# chunker later uses to split notes sensibly. Plain text is the fallback.
EXPORT_TYPES = ["text/markdown", "text/plain"]


def build_service():
    """Authenticate via service account or user OAuth, whichever is configured."""
    import os

    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("google-api-python-client is not installed — "
              "pip install -r scripts/requirements.txt", file=sys.stderr)
        raise SystemExit(2)

    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES
        )
        return build("drive", "v3", credentials=creds)

    secrets = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRETS")
    if secrets:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if TOKEN_CACHE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_CACHE), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds = InstalledAppFlow.from_client_secrets_file(
                    secrets, SCOPES
                ).run_local_server(port=0)
            TOKEN_CACHE.write_text(creds.to_json())
        return build("drive", "v3", credentials=creds)

    print("No Google credentials configured. Set either "
          "GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_OAUTH_CLIENT_SECRETS "
          "(see the docstring at the top of this file).", file=sys.stderr)
    raise SystemExit(2)


def export_doc(service, doc_id: str) -> str:
    """Export one Doc, preferring Markdown."""
    from googleapiclient.errors import HttpError

    last_error = None
    for mime in EXPORT_TYPES:
        try:
            return service.files().export(
                fileId=doc_id, mimeType=mime
            ).execute().decode("utf-8")
        except HttpError as exc:
            last_error = exc
            # 400 means this doc cannot be exported as that type; try the next.
            if exc.resp.status != 400:
                raise
    raise last_error


def pending_docs(index: dict, force: bool) -> list[tuple[str, str, str]]:
    """(note_date, doc_id, title) for every note whose body is still missing."""
    out = []
    for note in index["notes"]:
        if note.get("source_type") != "google_doc":
            continue
        for doc_id in note.get("doc_ids", []):
            if not force and (DOCS / f"{doc_id}.md").exists():
                continue
            out.append((note.get("note_date") or "", doc_id, note["title"]))
    return sorted(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="stop after N documents")
    parser.add_argument("--force", action="store_true",
                        help="re-export documents already on disk")
    parser.add_argument("--list", action="store_true",
                        help="list what needs extracting and exit")
    args = parser.parse_args()

    if not INDEX.exists():
        print(f"missing {INDEX.relative_to(ROOT)} — run scripts/build_index.py first",
              file=sys.stderr)
        return 1

    index = json.loads(INDEX.read_text())
    todo = pending_docs(index, args.force)
    if args.limit:
        todo = todo[: args.limit]

    if args.list:
        for note_date, doc_id, title in todo:
            print(f"{note_date}  {doc_id}  {title}")
        print(f"\n{len(todo)} document(s) pending")
        return 0

    if not todo:
        print("nothing to extract — every document is already on disk")
        return 0

    DOCS.mkdir(parents=True, exist_ok=True)
    service = build_service()

    ok, failed = 0, []
    for note_date, doc_id, title in todo:
        try:
            text = export_doc(service, doc_id)
        except Exception as exc:  # noqa: BLE001 - one bad doc must not stop the run
            failed.append((doc_id, title, str(exc).split("\n")[0]))
            print(f"  FAIL {note_date}  {title}: {exc}", file=sys.stderr)
            continue

        (DOCS / f"{doc_id}.md").write_text(text)
        ok += 1
        print(f"  ok   {note_date}  {title}  ({len(text.split())} words)")
        time.sleep(0.2)  # stay well inside Drive's per-user rate limit

    print(f"\nextracted {ok}/{len(todo)}")
    if failed:
        print(f"{len(failed)} failed:")
        for doc_id, title, err in failed:
            print(f"  {doc_id}  {title}  — {err}")
        print("\nMost failures are permissions: share the doc (or its parent "
              "folder) with the service account's client_email, read-only.")
    print("\nNext: python3 scripts/load_supabase.py")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
