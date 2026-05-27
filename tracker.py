"""Minimal visit/click tracker backed by SQLite.

Visits and clicks are stored as raw rows with a unix timestamp; the dashboard
aggregates at query time. SQLite is fine for personal-traffic scale and keeps
the deploy footprint tiny.
"""
import os
import sqlite3
import time
from contextlib import contextmanager

DB_PATH = os.environ.get(
    "TRACKER_DB",
    os.path.join(os.path.dirname(__file__), "data", "tracker.db"),
)

ALLOWED_SITES = {
    "javimendoza.com",
    "app.javimendoza.com",
    "links.javimendoza.com",
}


@contextmanager
def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY,
                site TEXT NOT NULL,
                path TEXT NOT NULL,
                ts INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_visits_site_ts ON visits(site, ts);

            CREATE TABLE IF NOT EXISTS clicks (
                id INTEGER PRIMARY KEY,
                slug TEXT NOT NULL,
                ts INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_clicks_slug_ts ON clicks(slug, ts);
        """)


def log_visit(site: str, path: str):
    if site not in ALLOWED_SITES:
        return
    with _conn() as con:
        con.execute(
            "INSERT INTO visits (site, path, ts) VALUES (?, ?, ?)",
            (site, path[:200], int(time.time())),
        )


def log_click(slug: str):
    with _conn() as con:
        con.execute(
            "INSERT INTO clicks (slug, ts) VALUES (?, ?)",
            (slug, int(time.time())),
        )


def get_stats():
    """Returns a dict with per-site visit totals and per-slug click totals,
    bucketed by today / last 7d / last 30d / all time."""
    now = int(time.time())
    day = 86400
    buckets = {
        "today": now - day,
        "week": now - 7 * day,
        "month": now - 30 * day,
        "all": 0,
    }

    with _conn() as con:
        visits_by_site = {}
        for site in sorted(ALLOWED_SITES):
            visits_by_site[site] = {
                label: con.execute(
                    "SELECT COUNT(*) FROM visits WHERE site = ? AND ts >= ?",
                    (site, since),
                ).fetchone()[0]
                for label, since in buckets.items()
            }

        slug_rows = con.execute(
            "SELECT slug, COUNT(*) AS total FROM clicks GROUP BY slug ORDER BY total DESC"
        ).fetchall()
        clicks_by_slug = []
        for row in slug_rows:
            slug = row["slug"]
            clicks_by_slug.append({
                "slug": slug,
                **{
                    label: con.execute(
                        "SELECT COUNT(*) FROM clicks WHERE slug = ? AND ts >= ?",
                        (slug, since),
                    ).fetchone()[0]
                    for label, since in buckets.items()
                },
            })

    return {"visits": visits_by_site, "clicks": clicks_by_slug}
