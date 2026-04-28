"""Re-run classification on existing notes and move misfiled ones.

Looks at every note under data/notes/<category>/<video_id>.md, reads the
cached transcript at data/transcripts/<video_id>.txt, asks Claude to
re-classify, and moves the note to the new category folder when it
differs.

Skips videos that have no cached transcript (would need to be re-fetched).
By default scans all categories; pass folder names to limit scope.

Usage:
    uv run python scripts/07_reclassify.py
    uv run python scripts/07_reclassify.py business other
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from anthropic import RateLimitError

from wl_cleanup.summarize import classify

NOTES_DIR = Path("data/notes")
TRANSCRIPTS_DIR = Path("data/transcripts")
RATE_LIMIT_BACKOFF = 70


def _classify_with_retry(transcript: str) -> str:
    for attempt in range(3):
        try:
            return classify(transcript)
        except RateLimitError:
            if attempt == 2:
                raise
            wait = RATE_LIMIT_BACKOFF * (attempt + 1)
            print(f"  rate-limited, sleeping {wait}s")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def main() -> None:
    targets = sys.argv[1:]
    if targets:
        cat_dirs = [NOTES_DIR / c for c in targets]
    else:
        cat_dirs = [d for d in NOTES_DIR.iterdir() if d.is_dir()]

    moved = 0
    unchanged = 0
    skipped = 0
    for cat_dir in cat_dirs:
        if not cat_dir.exists():
            continue
        for note in sorted(cat_dir.glob("*.md")):
            video_id = note.stem
            transcript_path = TRANSCRIPTS_DIR / f"{video_id}.txt"
            if not transcript_path.exists():
                print(f"[{video_id}] no cached transcript, skipping")
                skipped += 1
                continue
            transcript = transcript_path.read_text(encoding="utf-8")
            new_cat = _classify_with_retry(transcript)
            if new_cat == cat_dir.name:
                print(f"[{video_id}] {cat_dir.name} (unchanged)")
                unchanged += 1
                continue
            new_dir = NOTES_DIR / new_cat
            new_dir.mkdir(parents=True, exist_ok=True)
            new_path = new_dir / f"{video_id}.md"
            note.rename(new_path)
            print(f"[{video_id}] moved {cat_dir.name} -> {new_cat}")
            moved += 1

    print(f"\nDone. Moved: {moved}. Unchanged: {unchanged}. Skipped: {skipped}.")


if __name__ == "__main__":
    main()
