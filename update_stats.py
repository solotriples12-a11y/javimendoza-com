"""Fetch YouTube + Instagram follower counts and write them to stats.json.

Run once a day via cron. Flask reads the JSON, no live API calls per request.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_HANDLE = os.environ.get("YOUTUBE_HANDLE", "Javi-Tech")
INSTAGRAM_HANDLE = os.environ.get("INSTAGRAM_HANDLE", "javimendozayt")
STATS_FILE = os.environ.get("STATS_FILE", "stats.json")


def _parse_count(s: str) -> int:
    """Parse '856', '1,234', '1.2K', '3.4M' into an int."""
    s = s.strip()
    if s and s[-1] in "KkMm":
        suffix = s[-1].lower()
        num = float(s[:-1].replace(",", ""))
        mult = 1000 if suffix == "k" else 1_000_000
        return int(num * mult)
    return int(s.replace(",", ""))


def fetch_youtube() -> int:
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY not set")
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={
            "forHandle": YOUTUBE_HANDLE,
            "part": "statistics",
            "key": YOUTUBE_API_KEY,
        },
        timeout=10,
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError(f"YouTube channel not found: {YOUTUBE_HANDLE}")
    return int(items[0]["statistics"]["subscriberCount"])


def fetch_instagram() -> int:
    """Fetch follower count from Instagram.

    Tries the internal web_profile_info endpoint first (returns exact count as JSON),
    falls back to scraping HTML patterns if the API is blocked.
    """
    base_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Strategy A: internal web_profile_info JSON endpoint (used by IG's own frontend)
    try:
        api_headers = {
            **base_headers,
            "X-IG-App-ID": "936619743392459",
            "Accept": "*/*",
            "Referer": f"https://www.instagram.com/{INSTAGRAM_HANDLE}/",
        }
        r = requests.get(
            f"https://www.instagram.com/api/v1/users/web_profile_info/?username={INSTAGRAM_HANDLE}",
            headers=api_headers,
            timeout=10,
        )
        if r.ok:
            data = r.json()
            user = data.get("data", {}).get("user") or {}
            count = (user.get("edge_followed_by") or {}).get("count")
            if count is not None:
                print(f"  [ig] matched web_profile_info API (exact)")
                return int(count)
    except Exception as e:
        print(f"  [ig] web_profile_info API failed: {e}", file=sys.stderr)

    # Strategy B: fall back to scraping the public profile HTML
    html_headers = {
        **base_headers,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    r = requests.get(
        f"https://www.instagram.com/{INSTAGRAM_HANDLE}/",
        headers=html_headers,
        timeout=10,
    )
    r.raise_for_status()
    html = r.text

    # Try exact-count patterns first (these give the precise integer).
    # Fall back to og:description (which IG rounds to "18K") only if nothing exact found.

    # Pattern 1 (exact): edge_followed_by JSON blob
    m = re.search(r'"edge_followed_by":\s*\{\s*"count":\s*(\d+)\s*\}', html)
    if m:
        print(f"  [ig] matched edge_followed_by (exact)")
        return int(m.group(1))

    # Pattern 2 (exact): direct follower_count field
    m = re.search(r'"follower_count":\s*(\d+)', html)
    if m:
        print(f"  [ig] matched follower_count (exact)")
        return int(m.group(1))

    # Pattern 3 (exact): title="18,391" attribute near "followers" text.
    # IG shows the rounded "18.3K" visible, but keeps the exact integer
    # in the title attribute as a tooltip.
    idx = html.find("followers")
    if idx > 0:
        snippet = html[max(0, idx - 800):idx]
        titles = re.findall(r'title="([\d,]+)"', snippet)
        if titles:
            candidate = titles[-1]  # closest title to "followers"
            try:
                count = int(candidate.replace(",", ""))
                print(f"  [ig] matched title near 'followers' (exact): '{candidate}'")
                return count
            except ValueError:
                pass

    # Pattern 4 (rounded): og:description meta tag
    m = re.search(r'<meta property="og:description" content="([^"]+)"', html)
    if m:
        c = re.search(r"([\d,.]+[KkMm]?)\s*Followers", m.group(1))
        if c:
            print(f"  [ig] matched og:description (rounded): '{c.group(1)}'")
            return _parse_count(c.group(1))

    # All patterns failed — dump response for diagnosis
    debug_path = "ig_debug.html"
    with open(debug_path, "w") as f:
        f.write(html)
    raise RuntimeError(
        f"No follower count pattern matched "
        f"(HTTP {r.status_code}, final URL {r.url}, {len(html)} chars). "
        f"Response dumped to {debug_path}."
    )


def main() -> int:
    existing = {}
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE) as f:
                existing = json.load(f)
        except Exception:
            pass

    stats = {"updated_at": datetime.now(timezone.utc).isoformat()}
    errors = []

    for key, fetcher in [("youtube", fetch_youtube), ("instagram", fetch_instagram)]:
        try:
            stats[key] = fetcher()
            print(f"[OK] {key}: {stats[key]}")
        except Exception as e:
            errors.append(f"{key}: {e}")
            print(f"[FAIL] {key}: {e}", file=sys.stderr)
            # Keep last known good value if available
            if key in existing:
                stats[key] = existing[key]
                print(f"       fallback to last known value: {stats[key]}", file=sys.stderr)

    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

    return 1 if len(errors) == 2 else 0


if __name__ == "__main__":
    sys.exit(main())
