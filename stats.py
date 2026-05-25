"""Read precomputed follower counts from stats.json.

The actual fetching happens in update_stats.py (run by cron).
"""

import json
import os
from typing import Optional

STATS_FILE = os.environ.get("STATS_FILE", "stats.json")


def _load() -> dict:
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _format_count(n: Optional[int]) -> str:
    if n is None:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.1f}K".replace(".0K", "K")
    return str(n)


def get_youtube_stats() -> dict:
    n = _load().get("youtube")
    return {"count": n, "display": _format_count(n)}


def get_instagram_stats() -> dict:
    n = _load().get("instagram")
    return {"count": n, "display": _format_count(n)}
