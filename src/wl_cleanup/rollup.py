"""Consolidate per-video notes in a category folder into one synthesis."""
from __future__ import annotations

import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192

ROLLUP_PROMPT = """You are consolidating notes from {n} YouTube videos in
the "{category}" category into a single reference document for the
viewer. The viewer is building a side business and wants this document
to surface concrete things they can make and sell, in addition to the
usual themes and resources.

Each note below was generated from a separate video transcript and is
delimited by a header line of the form `===== <video_id> =====`.

Produce a single markdown document that:

1. Opens with a one-paragraph orientation explaining what topics this
   category covers across the videos.
2. **Sellable products & ideas to mimic** - the most valuable section.
   Concrete, specific physical products / SKUs / project types the
   videos describe being made and sold (e.g. "engraved slate
   coasters", "articulated dragon figurine", "raccoon meme t-shirt").
   Group by sub-type or material when possible. Cite video IDs in
   parentheses. Include any pricing, margin, sales-volume, or
   target-market cues. Skip this section only if the category has zero
   sellable-product content (e.g. ai-claude-code, business advice).
3. **Recurring themes & frameworks** - ideas, mental models, or
   strategies that appear in more than one video, with video IDs cited.
4. **Consolidated action items** - merge overlapping tactics, dedupe,
   group by sub-topic. Imperative voice.
5. **Tools, products, and resources mentioned** - things the viewer
   would buy or use (machines, software, suppliers, platforms), not
   things they would sell. Alphabetical, brief context.
6. **Outliers and one-offs** - interesting ideas that only appeared in
   a single video and don't fit the patterns above.
7. **Per-video index** - a short bulleted list, one line per video,
   format `- <video_id>: <one-sentence takeaway>`.

Be tight. No filler. Headings as markdown.

Notes:
{notes}
"""


UPDATE_PROMPT = """You are updating an existing rollup document for the
"{category}" category with {n} new video notes. The existing rollup
follows, then the new notes (each delimited by `===== <video_id> =====`).

Produce an updated version of the rollup that:

- Keeps the same seven-section structure (orientation, sellable products
  & ideas to mimic, recurring themes, consolidated action items, tools/
  resources, outliers, per-video index).
- If the existing rollup is missing the "Sellable products & ideas to
  mimic" section, add it now by re-deriving from existing + new notes.
- Folds new sellable products / themes / tactics into existing entries
  where they overlap; adds video IDs to the parenthetical citations.
- Promotes outliers to the recurring-themes section if the new notes
  reinforce them.
- Adds new tools alphabetically; merges entries if the same tool is
  mentioned with new context.
- Appends new entries to the per-video index. Do not drop existing
  index entries.

Be tight. Output the full updated markdown document.

Existing rollup:
{existing}

New notes:
{new_notes}
"""


def _client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. See .env.example.")
    return Anthropic(api_key=api_key)


def _format_notes(files: list[Path]) -> str:
    parts: list[str] = []
    for f in files:
        parts.append(f"===== {f.stem} =====\n{f.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


def _llm_call(prompt: str) -> str:
    msg = _client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if block.type == "text").strip()


def rollup_category(
    category_dir: Path, existing_rollup: Path | None = None, manifest: Path | None = None
) -> tuple[str, list[str]]:
    """Roll up notes in category_dir. Returns (rollup_text, included_ids).

    If manifest exists and lists video_ids already rolled up, only new
    notes get sent to the model; the existing rollup is updated rather
    than regenerated from scratch.
    """
    files = sorted(category_dir.glob("*.md"))
    if not files:
        raise RuntimeError(f"No notes in {category_dir}")

    already: set[str] = set()
    if manifest and manifest.exists():
        already = set(json.loads(manifest.read_text(encoding="utf-8")))

    new_files = [f for f in files if f.stem not in already]
    all_ids = [f.stem for f in files]

    if not already or not existing_rollup or not existing_rollup.exists():
        prompt = ROLLUP_PROMPT.format(
            n=len(files), category=category_dir.name, notes=_format_notes(files)
        )
        return _llm_call(prompt), all_ids

    if not new_files:
        return existing_rollup.read_text(encoding="utf-8"), all_ids

    prompt = UPDATE_PROMPT.format(
        n=len(new_files),
        category=category_dir.name,
        existing=existing_rollup.read_text(encoding="utf-8"),
        new_notes=_format_notes(new_files),
    )
    return _llm_call(prompt), all_ids
