# YouTube Insights

Personal tooling that turns YouTube videos into something useful, via one core idea:
pull a transcript, let Claude extract the value. Two capabilities live here.

**1. Watch Later cleanup** (`src/`, `scripts/`, `data/`) - the original tool, documented in
full below. Prunes my YouTube Watch Later backlog. The YouTube Data API v3 cannot read or
modify Watch Later (system-managed playlist, permission denied even with the right ID). A
Playwright approach was also tried but Google's bot detection blocks scripted logins, so
the current design extracts data via a DevTools console bookmarklet run in the user's real,
signed-in browser.

**2. Idea mining** (`idea-mining/`) - drop in YouTube URLs, fetch transcripts, mine them for
ideas. Transcripts (with a title/channel/URL header) go in `idea-mining/transcripts/`,
extracted insights in `idea-mining/insights/`. Fetching reuses `fetch_transcript` from
`src/wl_cleanup/summarize.py` (transcriptapi.com primary, yt-dlp fallback, cached). The
transcriptapi response is JSON, so parse the `transcript` field. For long transcripts,
analyze with a subagent rather than loading the raw text into the main thread. The internal
Python package stays named `wl_cleanup` (renaming it would break the working cleanup tool).

## Stack

- Python 3.11+ (managed with uv)
- Browser bookmarklet (DOM scrape in the signed-in browser) for data capture
- SQLite (stdlib `sqlite3`) for local state
- Anthropic SDK for categorization (default model: `claude-haiku-4-5`)
- Streamlit for the review dashboard

## Architecture

Three Python stages plus one manual browser step:

1. **Bookmarklet** (copy from README) - paste into DevTools console on the
   WL page, downloads `wl.json` with every row in view.
2. **`scripts/02_ingest.py`** - loads `data/wl.json`, upserts rows into
   `data/watch_later.db`.
3. **`scripts/03_categorize.py`** - reads uncategorized rows, two-pass
   clustering via Claude (propose clusters, then assign), writes back.
4. **Dashboard** - `streamlit run src/wl_cleanup/dashboard.py` reads the DB,
   provides filters (category, channel, watched %) and checkboxes, exports
   selected IDs to `flags.json`.

Removal (stage 5) is not yet implemented. The plan is a second bookmarklet
that reads `flags.json` IDs and clicks through the three-dot menu on each
row in the signed-in browser. Must be sequential with 1-2s jitter and capped
per run to avoid rate-limiting.

## Data model

```sql
CREATE TABLE videos (
    video_id         TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    channel          TEXT NOT NULL,
    duration_seconds INTEGER,
    added_at_text    TEXT,          -- usually empty on WL; kept for schema parity
    scraped_at       TIMESTAMP NOT NULL,
    category         TEXT,          -- nullable, set by stage 3
    category_reason  TEXT,          -- nullable, set by stage 3
    removed_at       TIMESTAMP,     -- nullable, set by the remover
    watched_percent  INTEGER DEFAULT 0  -- 0 unwatched, 100 fully watched
);
```

Upserts on `video_id` refresh `scraped_at`, `added_at_text`, and
`watched_percent` without losing category assignments.

## Commands

```bash
uv sync                                               # install deps
cp .env.example .env                                  # then add ANTHROPIC_API_KEY
# paste bookmarklet into DevTools on the WL page, download wl.json to data/
uv run python scripts/02_ingest.py                    # import wl.json into DB
uv run python scripts/03_categorize.py                # LLM clustering
uv run streamlit run src/wl_cleanup/dashboard.py      # review, export flags.json
```

## Gotchas

**Google blocks scripted logins.** Chromium driven by Playwright gets the
"Couldn't sign you in. This browser or app may not be secure." screen. Don't
try to work around it; use the bookmarklet in the real browser instead.

**WL rows are sparse.** No view count, no upload date, no description on the
playlist page. Title + channel + duration + watched % is all that's
available without fetching each video page individually.

**Scroll before extracting.** The bookmarklet only sees rows currently
rendered. Press End repeatedly on the WL page until the count stops growing,
then run the snippet.

**Do not use the YouTube Data API for Watch Later.** It will return
permission denied. Custom playlists are fine; WL is not.

## Code style

- No em dashes anywhere. Use commas, colons, or parentheses instead.
- Type hints on all public function signatures.
- `pathlib.Path` over `os.path`.
- Docstrings for public functions, not internal helpers.
- Ruff + black, 100-char line length.
- No ORM, plain `sqlite3` with named parameters.
- Keep `scripts/*.py` thin. Real logic lives in `src/wl_cleanup/`.
- Use `from __future__ import annotations` at the top of every module.

## What not to do

- Do not commit `.env`, `data/*.db`, `data/wl.json`, or `flags.json`
- Do not auto-remove based on category alone. Removal is always user-gated
  through the dashboard checkboxes.
- Do not call any YouTube Data API endpoint for modifying WL
- Do not try to reintroduce Playwright for login. Google will block it.

## Testing approach

Manual. Two sanity checks worth running after changes:

1. Re-run the bookmarklet against WL, ingest, and verify the row count in
   the DB matches what YouTube shows at the top of the playlist page.
2. Flag one video in the dashboard, remove it (once the remover exists),
   verify it disappears from WL and `removed_at` is populated in the DB.

Unit tests can come later for pure functions in `db.py`, `ingest.py`, and
`categorize.py`.
