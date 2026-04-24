"""Two-pass categorization of Watch Later videos using Claude.

Pass 1: ask Claude to propose 8 to 12 cluster names that fit the corpus.
Pass 2: for each batch of videos, assign exactly one category from the
        proposed list.

Default model is claude-haiku-4-5 (fast, cheap, plenty for title-level
classification). Swap MODEL to claude-sonnet-4-6 if titles are ambiguous
and you want better judgment.
"""
from __future__ import annotations

import json
import os
import random
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

from wl_cleanup.db import get_conn, set_category, uncategorized

load_dotenv()

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 4096
BATCH_SIZE = 25
SAMPLE_FOR_PROPOSAL = 120  # cap tokens when proposing clusters

PROPOSE_PROMPT = """You are organizing a YouTube Watch Later backlog.

Below are titles and channel names from the user's saved videos. Propose
8 to 12 category names that cleanly cluster them. Guidelines:

- Categories should be topical and specific (eg "3D printing tutorials",
  "data engineering talks", "scuba diving trip reports"), not generic
  ("tech", "educational").
- Every video should fit in exactly one of your categories. Include a
  catch-all like "misc" only if truly needed.
- Return JSON with a single key "categories" containing the list.
  No prose, no markdown, just JSON.

Videos:
{videos}
"""

ASSIGN_PROMPT = """Assign each video below to exactly one category from
this list: {categories}

Return JSON as a list of objects with keys "video_id", "category", and
"reason" (a short phrase explaining the choice). No prose, no markdown.

Videos:
{videos}
"""

ASSIGN_OR_UNFIT_PROMPT = """Assign each video below to exactly one category
from this list: {categories}

If a video genuinely does not fit any of these categories, set its
"category" to the literal string "__unfit__" instead. Be conservative:
prefer fitting it into an existing category unless the topic is clearly
outside all of them.

Return JSON as a list of objects with keys "video_id", "category", and
"reason" (a short phrase). No prose, no markdown.

Videos:
{videos}
"""


def _client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. See .env.example.")
    return Anthropic(api_key=api_key)


def _format_videos(videos: list[dict]) -> str:
    lines = []
    for v in videos:
        lines.append(f"- id={v['video_id']} | {v['channel']} | {v['title']}")
    return "\n".join(lines)


def _call_json(client: Anthropic, prompt: str) -> Any:
    """Single API call that expects a JSON-only response."""
    msg = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text").strip()
    # Strip accidental markdown fences if the model adds them.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def propose_categories(client: Anthropic, videos: list[dict]) -> list[str]:
    """First pass: let Claude look at a sample and propose cluster names."""
    sample = random.sample(videos, min(SAMPLE_FOR_PROPOSAL, len(videos)))
    prompt = PROPOSE_PROMPT.format(videos=_format_videos(sample))
    data = _call_json(client, prompt)
    categories = data.get("categories") if isinstance(data, dict) else None
    if not categories:
        raise RuntimeError(f"Unexpected response shape: {data}")
    return list(categories)


def assign_categories(
    client: Anthropic, videos: list[dict], categories: list[str], *, allow_unfit: bool = False
) -> list[dict]:
    """Second pass: assign each video to exactly one category.

    If allow_unfit is True, videos that don't clearly fit any category may
    be labeled "__unfit__" for separate handling.
    """
    template = ASSIGN_OR_UNFIT_PROMPT if allow_unfit else ASSIGN_PROMPT
    results: list[dict] = []
    for start in range(0, len(videos), BATCH_SIZE):
        batch = videos[start : start + BATCH_SIZE]
        prompt = template.format(
            categories=json.dumps(categories),
            videos=_format_videos(batch),
        )
        data = _call_json(client, prompt)
        if not isinstance(data, list):
            raise RuntimeError(f"Expected list, got: {type(data).__name__}")
        results.extend(data)
        print(f"  assigned {start + len(batch)} / {len(videos)}")
    return results


def existing_categories(conn) -> list[str]:
    """Distinct non-null categories already present in the DB."""
    rows = conn.execute(
        "SELECT DISTINCT category FROM videos WHERE category IS NOT NULL ORDER BY category"
    ).fetchall()
    return [r[0] for r in rows if r[0]]


def categorize_all() -> None:
    conn = get_conn()
    videos = uncategorized(conn)
    if not videos:
        print("Nothing to categorize. All rows already have a category.")
        return
    print(f"Found {len(videos)} uncategorized videos.")

    client = _client()
    existing = existing_categories(conn)

    if existing:
        print(f"Reusing {len(existing)} existing categories: {existing}")
        print("Trying to fit new videos into existing categories...")
        first_pass = assign_categories(client, videos, existing, allow_unfit=True)

        fitted = [a for a in first_pass if a.get("category") != "__unfit__"]
        unfit_ids = {a["video_id"] for a in first_pass if a.get("category") == "__unfit__"}
        unfit_videos = [v for v in videos if v["video_id"] in unfit_ids]

        if unfit_videos:
            print(f"{len(unfit_videos)} did not fit. Proposing new categories for them...")
            new_cats = propose_categories(client, unfit_videos)
            print(f"Proposed new categories: {new_cats}")
            second_pass = assign_categories(client, unfit_videos, existing + new_cats)
            assignments = fitted + second_pass
        else:
            print("All new videos fit into existing categories.")
            assignments = fitted
    else:
        print("No existing categories. Proposing from scratch...")
        categories = propose_categories(client, videos)
        print(f"Proposed categories: {categories}")
        assignments = assign_categories(client, videos, categories)

    for a in assignments:
        set_category(conn, a["video_id"], a["category"], a.get("reason", ""))
    conn.commit()
    conn.close()
    print(f"Wrote {len(assignments)} category assignments.")
