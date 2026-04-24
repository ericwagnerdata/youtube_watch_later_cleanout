"""Roll up per-video notes into one synthesis per category.

Usage:
    uv run python scripts/06_rollup.py                      # all categories, incremental
    uv run python scripts/06_rollup.py 3d-printing          # one category, incremental
    uv run python scripts/06_rollup.py --rebuild            # ignore manifests, rebuild all

Incremental mode reads data/rollups/<category>.included.json to find
which notes are already rolled up, and only sends new notes to the model.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from wl_cleanup.rollup import rollup_category

NOTES_DIR = Path("data/notes")
ROLLUPS_DIR = Path("data/rollups")


def main() -> None:
    args = sys.argv[1:]
    rebuild = "--rebuild" in args
    targets = [a for a in args if a != "--rebuild"]

    if targets:
        cat_dirs = [NOTES_DIR / c for c in targets]
    else:
        cat_dirs = [d for d in NOTES_DIR.iterdir() if d.is_dir()]

    ROLLUPS_DIR.mkdir(parents=True, exist_ok=True)
    for cat_dir in cat_dirs:
        if not cat_dir.exists():
            print(f"Skipping {cat_dir.name}: directory not found.")
            continue
        n = len(list(cat_dir.glob("*.md")))
        if n == 0:
            print(f"Skipping {cat_dir.name}: no notes.")
            continue
        rollup_path = ROLLUPS_DIR / f"{cat_dir.name}.md"
        manifest = ROLLUPS_DIR / f"{cat_dir.name}.included.json"
        existing = None if rebuild else rollup_path
        manifest_arg = None if rebuild else manifest

        already = set()
        if manifest_arg and manifest_arg.exists():
            already = set(json.loads(manifest_arg.read_text(encoding="utf-8")))
        new_count = sum(1 for f in cat_dir.glob("*.md") if f.stem not in already)

        if new_count == 0 and not rebuild:
            print(f"Skipping {cat_dir.name}: nothing new since last rollup.")
            continue

        action = "Rebuilding" if rebuild else ("Initial" if not already else "Updating")
        print(f"{action} {cat_dir.name} ({new_count} new of {n} total)...")
        summary, ids = rollup_category(cat_dir, existing, manifest_arg)
        rollup_path.write_text(summary, encoding="utf-8")
        manifest.write_text(json.dumps(sorted(ids), indent=2), encoding="utf-8")
        print(f"  saved to {rollup_path}")


if __name__ == "__main__":
    main()
