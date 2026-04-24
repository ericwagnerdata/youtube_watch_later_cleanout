# Watch Later Cleanup

Personal tool for pruning my YouTube Watch Later backlog. The YouTube Data
API v3 cannot read or modify Watch Later, and Google blocks scripted
browser logins, so data is captured by pasting a bookmarklet into DevTools
on the signed-in WL page.

See `CLAUDE.md` for full architecture, data model, and gotchas.

## Quick start

```bash
uv sync
cp .env.example .env           # then add ANTHROPIC_API_KEY
```

1. Open <https://www.youtube.com/playlist?list=WL> in your signed-in
   browser. Press `End` repeatedly until the row count stops growing.
2. Open DevTools console, paste the bookmarklet snippet (see below), run
   it. A `wl.json` file downloads. Move it to `data/wl.json`.
3. Ingest, categorize, review:

```bash
uv run python scripts/02_ingest.py                 # wl.json -> SQLite
uv run python scripts/03_categorize.py             # Claude clusters + labels
uv run streamlit run src/wl_cleanup/dashboard.py   # review, export flags.json
```

Removal (stage 5) is not implemented yet. Plan: a second bookmarklet that
reads `flags.json` and clicks the three-dot remove menu on each row.

## Bookmarklet

Paste into DevTools console on the WL page after scrolling to the bottom.
Downloads `wl.json` matching the shape `scripts/02_ingest.py` expects.

```javascript
(() => {
  const rows = document.querySelectorAll('ytd-playlist-video-renderer');
  const out = [];
  rows.forEach(r => {
    const a = r.querySelector('a#video-title');
    if (!a) return;
    const url = new URL(a.href, location.origin);
    const video_id = url.searchParams.get('v');
    if (!video_id) return;
    const title = (a.title || a.textContent || '').trim();
    const ch = r.querySelector('ytd-channel-name a, #channel-name a');
    const channel = ch ? ch.textContent.trim() : '';
    const dur = r.querySelector('ytd-thumbnail-overlay-time-status-renderer #text, badge-shape .badge-shape-wiz__text');
    const duration_text = dur ? dur.textContent.trim() : '';
    const prog = r.querySelector('#progress');
    let watched_percent = 0;
    if (prog && prog.style && prog.style.width) {
      watched_percent = parseInt(prog.style.width, 10) || 0;
    }
    out.push({ video_id, title, channel, duration_text, added_at_text: '', watched_percent });
  });
  const blob = new Blob([JSON.stringify(out, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'wl.json';
  a.click();
  console.log('Exported', out.length, 'rows');
})();
```
