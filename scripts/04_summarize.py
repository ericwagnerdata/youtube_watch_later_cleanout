"""Summarize a YouTube video given its URL or video ID.

Usage:
    uv run python scripts/04_summarize.py <url-or-video-id> [--save] \
        [--category 3d-printing|laser-engraving|print-on-demand|other]

With --save, writes the summary to
data/notes/<category>/<video_id>.md. Category is auto-classified unless
--category is passed.
"""
from __future__ import annotations

import sys
from pathlib import Path

from wl_cleanup.summarize import (
    CATEGORIES,
    classify,
    extract_video_id,
    fetch_transcript,
    summarize,
)

NOTES_DIR = Path("data/notes")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    save = "--save" in args
    args = [a for a in args if a != "--save"]

    category = None
    if "--category" in args:
        i = args.index("--category")
        if i + 1 >= len(args):
            print("--category needs a value.")
            sys.exit(1)
        category = args[i + 1]
        if category not in CATEGORIES:
            print(f"Category must be one of: {', '.join(CATEGORIES)}")
            sys.exit(1)
        del args[i : i + 2]

    if not args:
        print("Missing URL or video ID.")
        sys.exit(1)

    video_id = extract_video_id(args[0])
    print(f"Fetching transcript for {video_id}...")
    transcript = fetch_transcript(video_id)
    print(f"Transcript length: {len(transcript)} chars.")

    if category is None:
        print("Classifying...")
        category = classify(transcript)
        print(f"Category: {category}")

    print("Summarizing...")
    summary = summarize(transcript)

    if save:
        out_dir = NOTES_DIR / category
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{video_id}.md"
        out.write_text(summary, encoding="utf-8")
        print(f"Saved to {out}")

    safe = summary.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8"
    )
    print("\n" + safe + "\n")


if __name__ == "__main__":
    main()
