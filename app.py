"""
app.py
------
Flask server that:
  - Serves the frontend
  - Runs the complete AI presentation intelligence pipeline
  - Renders the approved generation package into PowerPoint
  - Returns the generated .pptx file for download
"""

import os
import re
import traceback

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
)
from flask_cors import CORS


load_dotenv()


from ai_engine.pipeline import (
    run_generation_pipeline,
)

from ai_engine.presentation_renderer import (
    render_presentation,
)
from ai_engine.gemini_client import (
    GeminiQuotaExceededError,
    GeminiTemporaryError,
)

app = Flask(__name__)

CORS(app)


def _safe_filename(
    title: str
) -> str:

    name = re.sub(
        r"[^a-zA-Z0-9_\- ]",
        "",
        title
    )

    name = (
        name
        .strip()
        .replace(
            " ",
            "_"
        )
    )

    return (
        f"{name or 'presentation'}.pptx"
    )


@app.route("/")
def home():

    return render_template(
        "index.html"
    )


@app.route(
    "/generate",
    methods=["POST"]
)
def generate():

    data = (
        request.get_json(
            force=True
        )
        or {}
    )

    title = str(
        data.get(
            "title",
            ""
        )
        or ""
    ).strip()

    audience = str(
        data.get(
            "audience",
            ""
        )
        or ""
    ).strip()

    tone = str(
        data.get(
            "tone",
            "confident and clear"
        )
        or "confident and clear"
    ).strip()

    try:

        num_slides = int(
            data.get(
                "num_slides",
                6
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "error":
            "Slides must be a valid integer."
        }), 400


    if not title:

        return jsonify({
            "error":
            "Please provide a presentation title."
        }), 400


    if num_slides < 3:

        return jsonify({
            "error":
            "A presentation must contain at least 3 slides."
        }), 400


    if num_slides > 12:

        return jsonify({
            "error":
            "A presentation can contain at most 12 slides."
        }), 400


    if not audience:

        audience = (
            "general professional audience"
        )


    if not os.environ.get(
        "GEMINI_API_KEY"
    ):

        return jsonify({
            "error":
            "GEMINI_API_KEY is not configured."
        }), 500


    try:

        print(
            "\n========================================"
        )

        print(
            "WEB GENERATION REQUEST"
        )

        print(
            "========================================"
        )

        print(
            f"Title: {title}"
        )

        print(
            f"Slides: {num_slides}"
        )

        print(
            f"Audience: {audience}"
        )

        print(
            f"Tone: {tone}"
        )

        print(
            "========================================\n"
        )


        generation_package = (
            run_generation_pipeline(
                title=title,
                total_slides=num_slides,
                audience=audience,
                tone=tone
            )
        )


        generation_status = (
            generation_package.get(
                "status"
            )
        )


        if (
            generation_status
            != "GENERATION_PACKAGE_READY"
        ):

            raise RuntimeError(
                "Generation pipeline did not "
                "produce a ready package. "
                f"Status: {generation_status}"
            )


        slide_deck = (
            generation_package.get(
                "slide_deck",
                {}
            )
        )


        generated_slides = (
            slide_deck.get(
                "slides",
                []
            )
        )


        if (
            len(generated_slides)
            != num_slides
        ):

            raise RuntimeError(
                "Generated slide count does not "
                "match the requested slide count. "
                f"Requested {num_slides}, "
                f"generated {len(generated_slides)}."
            )


        print(
            "[WEB SERVER] "
            "Rendering approved generation package..."
        )


        pptx_buffer = (
            render_presentation(
                generation_package
            )
        )


        print(
            "[WEB SERVER] "
            "Presentation ready for download."
        )


        return send_file(
            pptx_buffer,
            as_attachment=True,
            download_name=(
                _safe_filename(
                    title
                )
            ),
            mimetype=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            )
        )


    except GeminiQuotaExceededError:

        traceback.print_exc()

        return jsonify({
            "error":
            "AI generation quota is exhausted for today. "
            "Please try again after the API quota resets."
        }), 429


    except GeminiTemporaryError:

        traceback.print_exc()

        return jsonify({
            "error":
            "The AI presentation engine is temporarily busy. "
            "Please wait a few minutes and try again."
        }), 503


    except Exception as exc:

        traceback.print_exc()

        return jsonify({
            "error":
            "Presentation generation failed due to an "
            f"internal pipeline error: {exc}"
        }), 500


if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )