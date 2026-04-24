"""Import a JSON dump from the browser bookmarklet into the DB.

Format expected (list of objects with these keys):
    video_id, title, channel, duration_text, added_at_text, watched_percent

Extract rows from your signed-in browser via the DevTools console snippet
(see README), save to data/wl.json, then run scripts/02_ingest.py.
"""
from __future__ import annotations

import json
from pathlib import Path

from wl_cleanup.db import get_conn, upsert_video


def _parse_duration(text: str) -> int | None:
    """Convert "12:34" or "1:02:34" to seconds. Returns None if unparseable."""
    text = text.strip()
    if not text:
        return None
    parts = text.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return None


def ingest(path: Path) -> int:
    """Upsert rows from a browser-dumped JSON file into the DB.

    Returns the number of rows upserted.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    conn = get_conn()
    count = 0
    for entry in raw:
        video = {
            "video_id": entry["video_id"],
            "title": entry.get("title", "").strip() or "(untitled)",
            "channel": entry.get("channel", "").strip(),
            "duration_seconds": _parse_duration(entry.get("duration_text", "") or ""),
            "added_at_text": entry.get("added_at_text", ""),
            "watched_percent": int(entry.get("watched_percent") or 0),
        }
        upsert_video(conn, video)
        count += 1
    conn.commit()
    conn.close()
    return count
