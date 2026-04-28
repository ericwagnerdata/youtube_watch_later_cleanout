"""Fetch a YouTube video transcript and summarize it with Claude.

Used for videos worth keeping notes on (business ideas, tutorials) before
removing them from Watch Later.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from anthropic import Anthropic
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

TRANSCRIPTS_DIR = Path("data/transcripts")

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 2048

CATEGORIES = [
    "3d-printing",
    "laser-engraving",
    "print-on-demand",
    "ai-claude-code",
    "business",
    "other",
]

CLASSIFY_PROMPT = """Classify the following YouTube video transcript into
exactly one of these categories: {categories}

- 3d-printing: anything centered on 3D printers, filament, resin, slicers,
  or printable models.
- laser-engraving: laser cutters/engravers, materials, settings, projects.
- print-on-demand: t-shirts, mugs, POD platforms (Printify, Printful,
  Merch by Amazon), trend research for designs to sell.
- ai-claude-code: Claude Code, Anthropic SDK, AI coding agents, MCP
  servers, agent skills/subagents/hooks, prompt engineering for coding
  workflows, comparisons of AI dev tools (Cursor, Copilot, Aider, etc.).
- business: general entrepreneurship, marketing, sales, productivity, side
  hustles, finance, or business strategy not tied to a specific craft above.
- other: anything that does not clearly fit the above.

Reply with just the category slug, nothing else.

Transcript (first 4000 chars):
{transcript}
"""

SUMMARIZE_PROMPT = """You are summarizing a YouTube video for a viewer who
plans to use it as reference material for a side business in 3D printing,
laser engraving, or print-on-demand. The transcript follows.

Write a tight summary that captures:

1. One-sentence overview of what the video is about.
2. Key ideas, frameworks, or concepts introduced (bulleted).
3. Concrete tips, tactics, or action items (bulleted, imperative voice).
4. **Sellable items / product ideas** - specific physical products,
   designs, SKUs, or item categories the video mentions being made and
   sold (e.g. "articulated dragon figurine", "engraved cutting board",
   "raccoon meme t-shirt"). Include any pricing, margins, or sales
   volume cues mentioned. Skip this section only if the video genuinely
   has no product ideas.
5. Tools, products, or resources mentioned (software, machines,
   platforms, suppliers - things you'd buy or use, not things you'd
   sell).
6. Anything skippable or filler the viewer can ignore.

Be concise. Skip pleasantries and intros. Use markdown headings.

Transcript:
{transcript}
"""


def extract_video_id(url_or_id: str) -> str:
    """Accept a full YouTube URL or a bare 11-char video ID."""
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        return url_or_id
    parsed = urlparse(url_or_id)
    if parsed.hostname in {"youtu.be"}:
        return parsed.path.lstrip("/")
    if parsed.hostname and "youtube.com" in parsed.hostname:
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
    raise ValueError(f"Could not parse a video ID from: {url_or_id}")


def fetch_transcript(video_id: str) -> str:
    """Return the transcript as a single newline-joined string.

    Caches successful fetches to data/transcripts/<video_id>.txt so the
    same video never gets re-fetched (and re-billed). Tries (in order):
    transcriptapi.com if TRANSCRIPT_API_KEY is set, then
    youtube-transcript-api, then yt-dlp.
    """
    cache_path = TRANSCRIPTS_DIR / f"{video_id}.txt"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    transcript = _fetch_transcript_uncached(video_id)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(transcript, encoding="utf-8")
    return transcript


def _fetch_transcript_uncached(video_id: str) -> str:
    if not os.environ.get("TRANSCRIPT_API_KEY"):
        raise RuntimeError("TRANSCRIPT_API_KEY not set in .env")
    return _fetch_transcript_transcriptapi(video_id)


def _fetch_transcript_transcriptapi(video_id: str) -> str:
    """Use transcriptapi.com (paid, ~$5/mo) to fetch transcripts."""
    import urllib.parse
    import urllib.request

    key = os.environ["TRANSCRIPT_API_KEY"]
    url = (
        "https://transcriptapi.com/api/v2/youtube/transcript?"
        + urllib.parse.urlencode(
            {"video_url": video_id, "format": "text", "include_timestamp": "false"}
        )
    )
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ),
            "Accept": "text/plain, application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    text = body.strip()
    if not text:
        raise RuntimeError("transcriptapi returned an empty transcript")
    return text


def _fetch_transcript_ytdlp(video_id: str) -> str:
    """Fallback: pull subtitles via yt-dlp and parse the VTT output."""
    import re
    import tempfile
    from pathlib import Path

    from yt_dlp import YoutubeDL

    cookies = Path("data/cookies.txt")
    with tempfile.TemporaryDirectory() as tmp:
        out_template = str(Path(tmp) / "%(id)s.%(ext)s")
        opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-US", "en-GB"],
            "subtitlesformat": "vtt",
            "format": "best",
            "ignore_no_formats_error": True,
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
        }
        if cookies.exists():
            opts["cookiefile"] = str(cookies)

        with YoutubeDL(opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

        vtt_files = list(Path(tmp).glob(f"{video_id}*.vtt"))
        if not vtt_files:
            raise RuntimeError("yt-dlp did not produce a VTT file")
        vtt = vtt_files[0].read_text(encoding="utf-8", errors="replace")

    lines: list[str] = []
    seen: set[str] = set()
    for raw in vtt.splitlines():
        ln = raw.strip()
        if not ln or ln.startswith("WEBVTT") or ln.startswith("NOTE") or "-->" in ln:
            continue
        if ln.isdigit() or ln.startswith("Kind:") or ln.startswith("Language:"):
            continue
        text = re.sub(r"<[^>]+>", "", ln).strip()
        if text and text not in seen:
            seen.add(text)
            lines.append(text)
    return "\n".join(lines)


def _client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. See .env.example.")
    return Anthropic(api_key=api_key)


def summarize(transcript: str) -> str:
    msg = _client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": SUMMARIZE_PROMPT.format(transcript=transcript)}],
    )
    return "".join(block.text for block in msg.content if block.type == "text").strip()


def classify(transcript: str) -> str:
    """Pick one of CATEGORIES based on the transcript. Falls back to 'other'."""
    prompt = CLASSIFY_PROMPT.format(
        categories=", ".join(CATEGORIES),
        transcript=transcript[:4000],
    )
    msg = _client().messages.create(
        model=MODEL,
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text").strip().lower()
    for cat in CATEGORIES:
        if cat in text:
            return cat
    return "other"


def summarize_url(url_or_id: str) -> str:
    video_id = extract_video_id(url_or_id)
    transcript = fetch_transcript(video_id)
    return summarize(transcript)
