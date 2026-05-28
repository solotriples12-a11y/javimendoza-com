import json
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, Response, abort, redirect, render_template, request

import stats
import tracker

load_dotenv()

app = Flask(__name__)
tracker.init_db()

with open(os.path.join(os.path.dirname(__file__), "redirects.json")) as f:
    REDIRECTS = json.load(f)

# 1x1 transparent GIF served by the tracking pixel endpoint
PIXEL = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)

# Substrings that, if present in the user agent, identify a non-human visitor.
# Match is case-insensitive. Kept aggressive on purpose — false positives on
# real users are unlikely with these strings, false negatives inflate stats.
BOT_UA_PATTERNS = (
    "bot", "crawler", "spider", "scrape", "preview", "fetch",
    "facebookexternalhit", "whatsapp", "telegram", "discord",
    "slack", "twitter", "linkedin", "pinterest", "embedly", "outbrain",
    "chatgpt", "gptbot", "claudebot", "anthropic", "perplexity",
    "bingpreview", "yahoo!", "yandex", "duckduck", "applebot",
    "ahrefs", "semrush", "moz.com", "majestic", "petalbot",
    "headlesschrome", "phantomjs", "puppeteer", "playwright", "selenium",
    "curl/", "wget/", "python-requests", "python-urllib", "go-http-client",
    "okhttp", "axios", "node-fetch", "java/", "ruby",
    "uptimerobot", "pingdom", "newrelic", "datadog", "statuscake", "monitor",
    "feedfetcher", "feedly", "rss",
)


def _is_bot():
    ua = (request.user_agent.string or "").lower()
    if not ua:
        return True
    return any(p in ua for p in BOT_UA_PATTERNS)


def _ua():
    return request.user_agent.string or ""


@app.route("/")
def index():
    if not _is_bot():
        tracker.log_visit("javimendoza.com", "/", _ua())
    return render_template(
        "index.html",
        youtube=stats.get_youtube_stats(),
        instagram=stats.get_instagram_stats(),
        current_year=datetime.now().year,
    )


@app.route("/api/track")
def api_track():
    if not _is_bot():
        tracker.log_visit(
            request.args.get("site", ""),
            request.args.get("path", "/"),
            _ua(),
        )
    response = Response(PIXEL, mimetype="image/gif")
    response.headers["Cache-Control"] = "no-store, must-revalidate"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/r/<slug>")
def redirect_slug(slug):
    target = REDIRECTS.get(slug)
    if not target:
        abort(404)
    if not _is_bot():
        tracker.log_click(slug, _ua())
    return redirect(target, code=302)


def _auth_ok():
    expected = os.environ.get("STATS_PASSWORD", "")
    auth = request.authorization
    return expected and auth and auth.password == expected


@app.route("/stats")
def stats_dashboard():
    if not _auth_ok():
        return Response(
            "Auth required", 401,
            {"WWW-Authenticate": 'Basic realm="Stats"'},
        )
    return render_template(
        "stats.html",
        data=tracker.get_stats(),
        user_agents=tracker.get_user_agents() if request.args.get("debug") else None,
        now=datetime.now(),
    )


@app.route("/stats/reset", methods=["POST"])
def stats_reset():
    if not _auth_ok():
        abort(401)
    tracker.reset_all()
    return redirect("/stats", code=302)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
