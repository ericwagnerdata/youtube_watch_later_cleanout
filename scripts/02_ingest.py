"""Ingest a browser-dumped wl.json into the local DB.

Usage: uv run python scripts/02b_ingest_json.py [path]
Defaults to data/wl.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

from wl_cleanup.ingest import ingest

if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/wl.json")
    if not path.exists():
        print(f"Not found: {path}")
        sys.exit(1)
    n = ingest(path)
    print(f"Upserted {n} rows from {path}.")
