"""
app.py
------
Flask server that:
  - Serves the frontend (templates/index.html + static/*)
  - Exposes POST /generate which takes {title, num_slides, audience, tone}
    and returns a .pptx file for download, generated in-memory (no files
    are permanently stored on disk).
"""

import os
import re
import traceback

from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS

load_dotenv()  # reads .env into environment variables
from ppt_generator import generate_outline, build_presentation


app = Flask(__name__)
CORS(app)


def _safe_filename(title: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_\- ]", "", title).strip().replace(" ", "_")
    return f"{name or 'presentation'}.pptx"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    num_slides = int(data.get("num_slides", 6))
    audience = data.get("audience", "general professional audience")
    tone = data.get("tone", "confident and clear")

    if not title:
        return jsonify({"error": "Please provide a presentation title."}), 400

    if not os.environ.get("GEMINI_API_KEY"):
        return jsonify({"error": "GEMINI_API_KEY is not set. Add it to your .env file."}), 500

    try:
        outline = generate_outline(title, num_slides=num_slides, audience=audience, tone=tone)
        pptx_buffer = build_presentation(outline, title)
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the frontend
        traceback.print_exc()
        return jsonify({"error": f"Generation failed: {exc}"}), 500

    return send_file(
        pptx_buffer,
        as_attachment=True,
        download_name=_safe_filename(title),
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
