"""Streamlit review dashboard.

Reads data/watch_later.db, offers filters by category, channel, and age,
and exports a list of flagged video IDs to flags.json for remove.py.

Run with: uv run streamlit run src/wl_cleanup/dashboard.py
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import streamlit as st

from wl_cleanup.db import get_conn, mark_removed

DB_PATH = Path("data/watch_later.db")
FLAGS_PATH = Path("flags.json")
YT_URL = "https://www.youtube.com/watch?v={}"


def _fmt_duration(seconds: int | None) -> str:
    if seconds is None:
        return ""
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


@st.cache_data
def load_videos() -> list[dict]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT video_id, title, channel, duration_seconds, added_at_text,
               category, category_reason, watched_percent
        FROM videos
        WHERE removed_at IS NULL
        ORDER BY channel, scraped_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _age_bucket(added_text: str) -> str:
    """Loose bucket based on YouTube's own "X ago" string."""
    t = (added_text or "").lower()
    if "year" in t or "years" in t:
        return "over a year"
    if "month" in t:
        n = "".join(c for c in t if c.isdigit())
        if n and int(n) >= 6:
            return "6 to 12 months"
        return "under 6 months"
    if "week" in t or "day" in t or "hour" in t or "minute" in t:
        return "under 6 months"
    return "unknown"


st.set_page_config(page_title="Watch Later Cleanup", layout="wide")
st.title("Watch Later cleanup")

videos = load_videos()
if not videos:
    st.warning("No videos in the DB yet. Run scripts/02_ingest.py first.")
    st.stop()

st.caption(f"{len(videos)} videos in your Watch Later")

# Filters
col1, col2, col3, col4, col5 = st.columns(5)
categories = sorted({v["category"] for v in videos if v["category"]})
watched_options = ["Unwatched (0%)", "Barely started (1-24%)",
                   "Partial (25-74%)", "Mostly watched (75-99%)",
                   "Fully watched (100%)"]
with col1:
    cat_filter = st.multiselect("Category", categories)
with col2:
    channel_filter = st.text_input("Channel contains")
with col3:
    watched_filter = st.multiselect("Watched", watched_options)
with col4:
    age_filter = st.multiselect(
        "Age",
        ["under 6 months", "6 to 12 months", "over a year", "unknown"],
    )
with col5:
    sort_choice = st.selectbox(
        "Sort", ["Channel", "Most watched", "Least watched", "Title"]
    )


def _watched_bucket(p: int) -> str:
    if p <= 0:
        return "Unwatched (0%)"
    if p < 25:
        return "Barely started (1-24%)"
    if p < 75:
        return "Partial (25-74%)"
    if p < 100:
        return "Mostly watched (75-99%)"
    return "Fully watched (100%)"


filtered = videos
if cat_filter:
    filtered = [v for v in filtered if v["category"] in cat_filter]
if channel_filter:
    needle = channel_filter.lower()
    filtered = [v for v in filtered if needle in (v["channel"] or "").lower()]
if watched_filter:
    filtered = [
        v for v in filtered
        if _watched_bucket(v["watched_percent"] or 0) in watched_filter
    ]
if age_filter:
    filtered = [v for v in filtered if _age_bucket(v["added_at_text"]) in age_filter]

if sort_choice == "Most watched":
    filtered.sort(key=lambda v: -(v["watched_percent"] or 0))
elif sort_choice == "Least watched":
    filtered.sort(key=lambda v: (v["watched_percent"] or 0))
elif sort_choice == "Title":
    filtered.sort(key=lambda v: (v["title"] or "").lower())

st.write(f"Showing {len(filtered)} of {len(videos)}")


def _do_mark_removed(video_id: str) -> None:
    conn = get_conn()
    mark_removed(conn, video_id)
    conn.commit()
    conn.close()
    st.session_state.flagged.discard(video_id)
    load_videos.clear()

# Flag checkboxes, grouped by category for scannability
if "flagged" not in st.session_state:
    st.session_state.flagged = set()

by_cat: dict[str, list[dict]] = {}
for v in filtered:
    by_cat.setdefault(v["category"] or "uncategorized", []).append(v)

for cat, items in sorted(by_cat.items()):
    with st.expander(f"{cat} ({len(items)})", expanded=False):
        for v in items:
            key = v["video_id"]
            watched = v["watched_percent"] or 0
            watched_str = f"watched {watched}%" if watched else "unwatched"
            url = YT_URL.format(key)
            meta = (
                f"[{v['title']}]({url})  ·  {v['channel']}  ·  "
                f"{_fmt_duration(v['duration_seconds'])}  ·  {watched_str}"
            )
            c1, c2, c3 = st.columns([0.05, 0.80, 0.15])
            with c1:
                checked = st.checkbox(
                    "flag", key=f"cb_{key}", label_visibility="collapsed"
                )
            with c2:
                st.markdown(meta)
            with c3:
                if st.button("Mark removed", key=f"rm_{key}"):
                    _do_mark_removed(key)
                    st.rerun()
            if checked:
                st.session_state.flagged.add(key)
            else:
                st.session_state.flagged.discard(key)

st.divider()
st.write(f"Flagged for removal: {len(st.session_state.flagged)}")

bcol1, bcol2 = st.columns(2)
with bcol1:
    if st.button("Export flags.json", type="primary"):
        FLAGS_PATH.write_text(json.dumps(sorted(st.session_state.flagged), indent=2))
        st.success(f"Wrote {len(st.session_state.flagged)} IDs to {FLAGS_PATH}")
with bcol2:
    if st.button("Mark all flagged as removed", disabled=not st.session_state.flagged):
        ids = list(st.session_state.flagged)
        conn = get_conn()
        for vid in ids:
            mark_removed(conn, vid)
        conn.commit()
        conn.close()
        st.session_state.flagged.clear()
        load_videos.clear()
        st.success(f"Marked {len(ids)} videos as removed")
        st.rerun()
