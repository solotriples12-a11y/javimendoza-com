from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template

import stats

load_dotenv()

app = Flask(__name__)


@app.route("/")
def index():
    return render_template(
        "index.html",
        youtube=stats.get_youtube_stats(),
        instagram=stats.get_instagram_stats(),
        current_year=datetime.now().year,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
