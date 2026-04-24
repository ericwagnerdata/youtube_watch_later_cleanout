"""Fetch a YouTube video transcript and summarize it with Claude.

Used for videos worth keeping notes on (business ideas, tutorials) before
removing them from Watch Later.
"""
from __future__ import annotations

import os
import re
from urllib.parse import parse_qs, urlparse

from anthropic import Anthropic
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 2048

CATEGORIES = ["3d-printing", "laser-engraving", "print-on-demand", "business", "other"]

CLASSIFY_PROMPT = """Classify the following YouTube video transcript into
exactly one of these categories: {categories}

- 3d-printing: anything centered on 3D printers, filament, resin, slicers,
  or printable models.
- laser-engraving: laser cutters/engravers, materials, settings, projects.
- print-on-demand: t-shirts, mugs, POD platforms (Printify, Printful,
  Merch by Amazon), trend research for designs to sell.
- business: general entrepreneurship, marketing, sales, productivity, side
  hustles, finance, or business strategy not tied to a specific craft above.
- other: anything that does not clearly fit the above.

Reply with just the category slug, nothing else.

Transcript (first 4000 chars):
{transcript}
"""

SUMMARIZE_PROMPT = """You are summarizing a YouTube video for a viewer who
plans to use it as reference material for a side business. The transcript
follows.

Write a tight summary that captures:

1. One-sentence overview of what the video is about.
2. Key ideas, frameworks, or concepts introduced (bulleted).
3. Concrete tips, tactics, or action items (bulleted, imperative voice).
4. Tools, products, or resources mentioned (bulleted, with brief context).
5. Anything skippable or filler the viewer can ignore.

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

    Tries youtube-transcript-api first, falls back to yt-dlp if that hits
    an IP block, request block, or other transient failure.
    """
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        return "\n".join(snippet.text for snippet in fetched)
    except Exception as e:
        print(f"  primary transcript fetch failed ({type(e).__name__}), trying yt-dlp...")
        return _fetch_transcript_ytdlp(video_id)


def _fetch_transcript_ytdlp(video_id: str) -> str:
    """Fallback: pull subtitles via yt-dlp and parse the VTT output."""
    import re
    import urllib.request

    from yt_dlp import YoutubeDL

    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

    subs = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    track = None
    for lang in ("en", "en-US", "en-GB"):
        if lang in subs:
            track = subs[lang]
            break
        if lang in auto:
            track = auto[lang]
            break
    if not track:
        raise RuntimeError("yt-dlp found no English subtitles")

    vtt_url = next((t["url"] for t in track if t.get("ext") == "vtt"), track[0]["url"])
    with urllib.request.urlopen(vtt_url) as resp:
        vtt = resp.read().decode("utf-8", errors="replace")

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
