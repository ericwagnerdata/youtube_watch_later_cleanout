"""Process every URL in data/queue.txt by running the summarizer.

Reads data/queue.txt line-by-line, summarizes each URL, and removes the
line on success. Lines that fail (e.g. transcript IpBlocked, no captions)
are left in place so you can retry later.
"""
from __future__ import annotations

import time
from pathlib import Path

from wl_cleanup.summarize import classify, extract_video_id, fetch_transcript, summarize

QUEUE_PATH = Path("data/queue.txt")
NOTES_DIR = Path("data/notes")
DELAY_SECONDS = 60


def _process(url: str) -> bool:
    video_id = extract_video_id(url)
    print(f"[{video_id}] fetching transcript...")
    transcript = fetch_transcript(video_id)
    print(f"[{video_id}] classifying...")
    category = classify(transcript)
    print(f"[{video_id}] category={category}, summarizing...")
    summary = summarize(transcript)
    out_dir = NOTES_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{video_id}.md").write_text(summary, encoding="utf-8")
    print(f"[{video_id}] saved to {out_dir / (video_id + '.md')}")
    return True


def main() -> None:
    if not QUEUE_PATH.exists():
        print(f"No queue file at {QUEUE_PATH}.")
        return
    lines = [ln.strip() for ln in QUEUE_PATH.read_text(encoding="utf-8").splitlines()]
    pending = [ln for ln in lines if ln and not ln.startswith("#")]
    if not pending:
        print("Queue is empty.")
        return

    print(f"Processing {len(pending)} URLs (sleeping {DELAY_SECONDS}s between)...\n")
    remaining: list[str] = []
    failures = 0
    for i, url in enumerate(pending):
        if i > 0:
            time.sleep(DELAY_SECONDS)
        try:
            _process(url)
        except Exception as e:
            failures += 1
            print(f"  FAILED: {type(e).__name__}: {e}")
            remaining.append(url)

    QUEUE_PATH.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
    done = len(pending) - len(remaining)
    print(f"\nDone. Summarized: {done}. Left in queue: {len(remaining)}. Failures: {failures}.")


if __name__ == "__main__":
    main()
