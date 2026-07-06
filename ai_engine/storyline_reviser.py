import json
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

MODEL = "gemini-3.5-flash"


STORYLINE_REVISER_PROMPT = """
You are the Storyline Reviser of a specialized AI presentation system.

You receive:

1. A Topic Analysis
2. A Presentation Storyline
3. A Quality Critique

Your job is to revise the storyline according to the critic's findings.

You are NOT creating a new unrelated presentation.

Preserve:
- the original topic
- the total slide count
- the strongest parts of the narrative
- the logical progression
- correct and useful concepts

Correct:
- technically overconfident claims
- unsupported absolute statements
- generic presentation language
- topic drift
- audience mismatch
- narrative gaps
- repetitive intellectual functions

Do not blindly rewrite every slide.

Only make changes that improve the presentation.

A revision should be surgical and evidence-driven.

If the critic identifies a specific phrase or claim,
directly correct that issue.

Never change the total number of slides.

Return ONLY valid JSON.
"""


def _extract_json(text: str) -> dict:
    cleaned = re.sub(
        r"^```(?:json)?|```$",
        "",
        text.strip(),
        flags=re.MULTILINE
    ).strip()

    return json.loads(cleaned)


def revise_storyline(
    topic_analysis: dict,
    storyline: dict,
    critique: dict
) -> dict:

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from .env file."
        )

    client = genai.Client(
        api_key=api_key
    )

    total_slides = storyline.get("total_slides")

    if not total_slides:
        raise RuntimeError(
            "Storyline does not contain total_slides."
        )

    topic_json = json.dumps(
        topic_analysis,
        indent=2
    )

    storyline_json = json.dumps(
        storyline,
        indent=2
    )

    critique_json = json.dumps(
        critique,
        indent=2
    )

    user_prompt = f"""
Revise the presentation storyline.

TOPIC ANALYSIS:

{topic_json}

CURRENT STORYLINE:

{storyline_json}

CRITIQUE:

{critique_json}

The revised storyline must contain EXACTLY {total_slides} slides.

Return JSON matching exactly this structure:

{{
  "topic": "presentation topic",

  "total_slides": {total_slides},

  "narrative_thesis": "revised central intellectual argument",

  "story_arc": "revised explanation of the presentation progression",

  "revision_summary": [
    "specific correction made",
    "specific correction made"
  ],

  "slides": [
    {{
      "slide_number": 1,
      "role": "opening",
      "purpose": "what this slide must accomplish",
      "core_message": "single corrected core message",
      "concepts_used": [],
      "transition_to_next": "logical transition"
    }}
  ]
}}

REVISION RULES:

1. Return exactly {total_slides} slides.

2. Preserve slide numbering.

3. Slide 1 must have role "opening".

4. Slide {total_slides} must have role "synthesis".

5. Correct every high severity issue.

6. Correct every medium severity issue.

7. Correct claims listed in claims_needing_qualification.

8. Remove every phrase listed in banned_phrases_detected.

9. Use revision_priority as the primary correction order.

10. Do not introduce new topic drift.

11. Do not invent statistics.

12. Do not replace precise technical language with marketing language.

13. Preserve strong slides when no correction is needed.

14. revision_summary must describe actual changes made.

15. Every slide must still have exactly one primary core message.

16. The revised narrative must continue answering the original core question.
"""

    try:
        print(
            "[STORYLINE REVISER] Revising storyline..."
        )

        max_retries = 4
        response = None

        for attempt in range(
            1,
            max_retries + 1
        ):
            try:
                print(
                    f"[STORYLINE REVISER] API attempt "
                    f"{attempt}/{max_retries}"
                )

                response = client.models.generate_content(
                    model=MODEL,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=STORYLINE_REVISER_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.15,
                        max_output_tokens=4000
                    )
                )

                break

            except Exception as api_error:
                error_text = str(api_error)

                temporary_error = (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "high demand" in error_text.lower()
                    or "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                )

                if (
                    not temporary_error
                    or attempt == max_retries
                ):
                    raise

                wait_seconds = 5 * attempt

                print(
                    "[STORYLINE REVISER] "
                    f"Temporary Gemini error. "
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)

        if response is None:
            raise RuntimeError(
                "Storyline Reviser did not receive a response."
            )

        if not response.text:
            raise RuntimeError(
                "Storyline Reviser returned an empty response."
            )

        revised_storyline = _extract_json(
            response.text
        )

        slides = revised_storyline.get("slides")

        if not isinstance(slides, list):
            raise RuntimeError(
                "Storyline Reviser returned invalid slides."
            )

        if len(slides) != total_slides:
            raise RuntimeError(
                "Storyline Reviser violated slide count. "
                f"Expected {total_slides}, "
                f"received {len(slides)}."
            )

        expected_numbers = list(
            range(
                1,
                total_slides + 1
            )
        )

        actual_numbers = [
            slide.get("slide_number")
            for slide in slides
        ]

        if actual_numbers != expected_numbers:
            raise RuntimeError(
                "Storyline Reviser returned invalid numbering. "
                f"Expected {expected_numbers}, "
                f"received {actual_numbers}."
            )

        if slides[0].get("role") != "opening":
            raise RuntimeError(
                "Revised Slide 1 must have role 'opening'."
            )

        if slides[-1].get("role") != "synthesis":
            raise RuntimeError(
                f"Revised Slide {total_slides} "
                "must have role 'synthesis'."
            )

        print(
            "[STORYLINE REVISER] "
            "Revision completed successfully."
        )

        return revised_storyline

    except Exception as error:
        print(
            "\n========== STORYLINE REVISER ERROR =========="
        )

        print(
            type(error).__name__
        )

        print(
            str(error)
        )

        print(
            "==============================================\n"
        )

        raise RuntimeError(
            f"Storyline revision failed: {error}"
        ) from error