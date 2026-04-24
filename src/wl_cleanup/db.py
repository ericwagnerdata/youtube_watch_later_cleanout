"""SQLite helpers for data/watch_later.db."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("data/watch_later.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    video_id         TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    channel          TEXT NOT NULL,
    duration_seconds INTEGER,
    added_at_text    TEXT,
    scraped_at       TIMESTAMP NOT NULL,
    category         TEXT,
    category_reason  TEXT,
    removed_at       TIMESTAMP,
    watched_percent  INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_category ON videos(category);
CREATE INDEX IF NOT EXISTS idx_removed  ON videos(removed_at);
"""


def get_conn() -> sqlite3.Connection:
    """Return a connection to the local DB, creating the schema if missing."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_video(conn: sqlite3.Connection, video: dict) -> None:
    """Insert a video row or refresh its scraped_at / added_at_text if it exists.

    Preserves category, category_reason, and removed_at across re-scrapes.
    """
    video = {
        **video,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    video.setdefault("watched_percent", 0)
    conn.execute(
        """
        INSERT INTO videos (video_id, title, channel, duration_seconds,
                            added_at_text, scraped_at, watched_percent)
        VALUES (:video_id, :title, :channel, :duration_seconds,
                :added_at_text, :scraped_at, :watched_percent)
        ON CONFLICT(video_id) DO UPDATE SET
            scraped_at      = excluded.scraped_at,
            added_at_text   = excluded.added_at_text,
            watched_percent = excluded.watched_percent
        """,
        video,
    )


def mark_removed(conn: sqlite3.Connection, video_id: str) -> None:
    """Stamp removed_at for a video that was successfully removed from WL."""
    conn.execute(
        "UPDATE videos SET removed_at = ? WHERE video_id = ?",
        (datetime.now(timezone.utc).isoformat(), video_id),
    )


def uncategorized(conn: sqlite3.Connection) -> list[dict]:
    """Return videos that still need a category assignment."""
    rows = conn.execute(
        "SELECT video_id, title, channel FROM videos "
        "WHERE category IS NULL AND removed_at IS NULL"
    ).fetchall()
    return [dict(r) for r in rows]


def set_category(conn: sqlite3.Connection, video_id: str, category: str, reason: str) -> None:
    """Write a category assignment back to the DB."""
    conn.execute(
        "UPDATE videos SET category = ?, category_reason = ? WHERE video_id = ?",
        (category, reason, video_id),
    )
