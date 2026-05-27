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


def _is_bot():
    ua = (request.user_agent.string or "").lower()
    return any(b in ua for b in ("bot", "crawler", "spider", "preview", "fetch"))


@app.before_request
def track_own_visits():
    if request.method != "GET":
        return
    if request.path.startswith(("/api/", "/r/", "/static/", "/stats")) or request.path == "/favicon.ico":
        return
    if _is_bot():
        return
    tracker.log_visit("javimendoza.com", request.path)


@app.route("/")
def index():
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
        tracker.log_click(slug)
    return redirect(target, code=302)


@app.route("/stats")
def stats_dashboard():
    expected = os.environ.get("STATS_PASSWORD", "")
    auth = request.authorization
    if not expected or not auth or auth.password != expected:
        return Response(
            "Auth required", 401,
            {"WWW-Authenticate": 'Basic realm="Stats"'},
        )
    return render_template("stats.html", data=tracker.get_stats(), now=datetime.now())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
