import json
import re

from ai_engine.gemini_client import (
    GeminiError,
    generate_json,
)


SLIDE_CONTENT_REVISER_PROMPT = """
You are the Slide Content Reviser of a specialized AI presentation system.

You receive:

1. A Topic Analysis
2. An approved Presentation Storyline
3. A generated Slide Deck
4. A structured Slide Content Critique

Your responsibility is to revise presentation content according to the critic's findings.

You are NOT redesigning the presentation storyline.

You must preserve:

- the original presentation topic
- the total slide count
- slide numbering
- slide roles
- the intellectual purpose of every slide
- the approved storyline
- strong slide content that does not require correction

You must correct:

- weak or generic titles
- vague bullets
- duplicated content
- technically overconfident claims
- unsupported absolute statements
- storyline drift
- generic presentation language
- unnecessary verbosity
- weak synthesis
- audience mismatch

Revision must be surgical.

Do not rewrite strong slides merely to make the wording different.

If the critic identifies a specific slide,
prioritize correction of that slide.

If the critic identifies a claim needing qualification,
rewrite the claim using technically careful wording.

If the critic identifies a banned phrase,
remove that phrase completely.

Return ONLY valid JSON.
"""


ALLOWED_CONTENT_TYPES = {
    "opening",
    "definition",
    "concept_explanation",
    "mechanism",
    "classification",
    "comparison",
    "process",
    "timeline",
    "application",
    "limitations",
    "evaluation",
    "synthesis",
}


def _extract_json(text: str) -> dict:
    cleaned = re.sub(
        r"^```(?:json)?|```$",
        "",
        text.strip(),
        flags=re.MULTILINE
    ).strip()

    return json.loads(cleaned)


def _validate_reviser_inputs(
    topic_analysis: dict,
    storyline: dict,
    slide_deck: dict,
    critique: dict
) -> None:

    inputs = {
        "topic_analysis": topic_analysis,
        "storyline": storyline,
        "slide_deck": slide_deck,
        "critique": critique,
    }

    for name, value in inputs.items():
        if not isinstance(value, dict):
            raise TypeError(
                f"{name} must be a dictionary."
            )

    required_topic_fields = [
        "topic",
        "presentation_goal",
        "core_question",
    ]

    missing_topic_fields = [
        field
        for field in required_topic_fields
        if field not in topic_analysis
    ]

    if missing_topic_fields:
        raise ValueError(
            "Slide Content Reviser received incomplete "
            "topic analysis. Missing fields: "
            f"{missing_topic_fields}"
        )

    required_storyline_fields = [
        "topic",
        "total_slides",
        "slides",
    ]

    missing_storyline_fields = [
        field
        for field in required_storyline_fields
        if field not in storyline
    ]

    if missing_storyline_fields:
        raise ValueError(
            "Slide Content Reviser received incomplete "
            "storyline. Missing fields: "
            f"{missing_storyline_fields}"
        )

    required_deck_fields = [
        "topic",
        "total_slides",
        "slides",
    ]

    missing_deck_fields = [
        field
        for field in required_deck_fields
        if field not in slide_deck
    ]

    if missing_deck_fields:
        raise ValueError(
            "Slide Content Reviser received incomplete "
            "slide deck. Missing fields: "
            f"{missing_deck_fields}"
        )

    required_critique_fields = [
        "overall_score",
        "decision",
        "issues",
        "banned_phrases_detected",
        "claims_needing_qualification",
        "duplicate_content",
        "revision_priority",
    ]

    missing_critique_fields = [
        field
        for field in required_critique_fields
        if field not in critique
    ]

    if missing_critique_fields:
        raise ValueError(
            "Slide Content Reviser received incomplete "
            "critique. Missing fields: "
            f"{missing_critique_fields}"
        )

    if critique["decision"] == "APPROVE":
        raise ValueError(
            "Slide Content Reviser should not revise "
            "an approved slide deck."
        )


def _validate_revised_slide(
    slide: dict,
    original_slide: dict,
    expected_number: int
) -> None:

    required_fields = [
        "slide_number",
        "role",
        "title",
        "subtitle",
        "content_type",
        "key_message",
        "bullets",
        "speaker_context",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in slide
    ]

    if missing_fields:
        raise RuntimeError(
            "Slide Content Reviser returned an incomplete "
            f"slide {expected_number}. Missing fields: "
            f"{missing_fields}"
        )

    if slide["slide_number"] != expected_number:
        raise RuntimeError(
            "Slide Content Reviser changed slide numbering. "
            f"Expected {expected_number}, received "
            f"{slide['slide_number']}."
        )

    original_role = original_slide.get("role")

    if slide["role"] != original_role:
        raise RuntimeError(
            "Slide Content Reviser changed the slide role. "
            f"Slide {expected_number} expected "
            f"'{original_role}', received '{slide['role']}'."
        )

    if slide["content_type"] not in ALLOWED_CONTENT_TYPES:
        raise RuntimeError(
            "Slide Content Reviser returned unsupported "
            f"content_type. Slide {expected_number}: "
            f"'{slide['content_type']}'."
        )

    text_fields = [
        "title",
        "key_message",
    ]

    for field in text_fields:
        value = slide[field]

        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise RuntimeError(
                f"Slide {expected_number} has invalid "
                f"{field}."
            )

    if not isinstance(
        slide["subtitle"],
        str
    ):
        raise RuntimeError(
            f"Slide {expected_number} subtitle "
            "must be a string."
        )

    if not isinstance(
        slide["speaker_context"],
        str
    ):
        raise RuntimeError(
            f"Slide {expected_number} speaker_context "
            "must be a string."
        )

    bullets = slide["bullets"]

    if not isinstance(bullets, list):
        raise RuntimeError(
            f"Slide {expected_number} bullets "
            "must be a list."
        )

    if len(bullets) > 4:
        raise RuntimeError(
            f"Slide {expected_number} contains too many "
            "bullets. A slide may contain at most 4 bullets."
        )

    normalized_bullets = []

    for bullet in bullets:

        if (
            not isinstance(bullet, str)
            or not bullet.strip()
        ):
            raise RuntimeError(
                f"Slide {expected_number} contains "
                "an empty or invalid bullet."
            )

        normalized_bullets.append(
            bullet.strip().lower()
        )

    if (
        len(normalized_bullets)
        != len(set(normalized_bullets))
    ):
        raise RuntimeError(
            f"Slide {expected_number} contains "
            "duplicate bullets."
        )


def _validate_revised_deck(
    revised_deck: dict,
    original_deck: dict
) -> None:

    required_fields = [
        "topic",
        "total_slides",
        "revision_summary",
        "slides",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in revised_deck
    ]

    if missing_fields:
        raise RuntimeError(
            "Slide Content Reviser returned invalid JSON. "
            f"Missing fields: {missing_fields}"
        )

    if (
        revised_deck["topic"]
        != original_deck["topic"]
    ):
        raise RuntimeError(
            "Slide Content Reviser changed the "
            "presentation topic."
        )

    if (
        revised_deck["total_slides"]
        != original_deck["total_slides"]
    ):
        raise RuntimeError(
            "Slide Content Reviser changed total_slides."
        )

    revision_summary = revised_deck[
        "revision_summary"
    ]

    if not isinstance(
        revision_summary,
        list
    ):
        raise RuntimeError(
            "revision_summary must be a list."
        )

    slides = revised_deck["slides"]

    if not isinstance(slides, list):
        raise RuntimeError(
            "Slide Content Reviser returned invalid slides."
        )

    expected_slide_count = original_deck[
        "total_slides"
    ]

    if len(slides) != expected_slide_count:
        raise RuntimeError(
            "Slide Content Reviser violated slide count. "
            f"Expected {expected_slide_count}, "
            f"received {len(slides)}."
        )

    original_slides = original_deck["slides"]

    if len(original_slides) != expected_slide_count:
        raise RuntimeError(
            "Original slide deck contains an invalid "
            "slide count."
        )

    for index, slide in enumerate(slides):

        expected_number = index + 1

        _validate_revised_slide(
            slide=slide,
            original_slide=original_slides[index],
            expected_number=expected_number
        )


def revise_slide_content(
    topic_analysis: dict,
    storyline: dict,
    slide_deck: dict,
    critique: dict
) -> dict:

    _validate_reviser_inputs(
        topic_analysis=topic_analysis,
        storyline=storyline,
        slide_deck=slide_deck,
        critique=critique
    )

    total_slides = slide_deck["total_slides"]

    topic_json = json.dumps(
        topic_analysis,
        indent=2
    )

    storyline_json = json.dumps(
        storyline,
        indent=2
    )

    deck_json = json.dumps(
        slide_deck,
        indent=2
    )

    critique_json = json.dumps(
        critique,
        indent=2
    )

    user_prompt = f"""
Revise this presentation slide content.

TOPIC ANALYSIS:

{topic_json}

APPROVED STORYLINE:

{storyline_json}

CURRENT SLIDE DECK:

{deck_json}

SLIDE CONTENT CRITIQUE:

{critique_json}

The revised slide deck must contain EXACTLY
{total_slides} slides.

Return JSON matching exactly this structure:

{{
  "topic": "{slide_deck['topic']}",
  "total_slides": {total_slides},

  "revision_summary": [
    "specific content correction made",
    "specific content correction made"
  ],

  "slides": [
    {{
      "slide_number": 1,
      "role": "opening",
      "title": "specific presentation title",
      "subtitle": "",
      "content_type": "opening",
      "key_message": "one primary message",
      "bullets": [],
      "speaker_context": "brief context for the presenter"
    }}
  ]
}}

REVISION RULES:

1. Return exactly {total_slides} slides.

2. Preserve every slide number.

3. Preserve every slide role exactly.

4. Preserve the approved storyline.

5. Correct every high severity issue.

6. Correct every medium severity issue.

7. Correct every claim listed in
   claims_needing_qualification.

8. Remove every phrase listed in
   banned_phrases_detected.

9. Resolve duplicate_content findings.

10. Follow revision_priority in order.

11. Do not invent statistics.

12. Do not introduce unsupported factual claims.

13. Do not use generic marketing language.

14. Keep at most 4 bullets per slide.

15. Every bullet must communicate a distinct idea.

16. Every slide must have one primary key_message.

17. Preserve strong slide content when no correction
    is required.

18. revision_summary must describe actual corrections.

19. Do not change content merely for stylistic variation.

20. The final deck must continue answering the original
    core question.
"""

    try:
        print(
            "[SLIDE CONTENT REVISER] "
            "Revising slide content..."
        )

        response_text = generate_json(
            system_prompt=SLIDE_CONTENT_REVISER_PROMPT,
            user_prompt=user_prompt,
            temperature=0.15,
            max_output_tokens=5000,
            caller_name="SLIDE CONTENT REVISER"
        )

        revised_deck = _extract_json(
            response_text
        )

        _validate_revised_deck(
            revised_deck=revised_deck,
            original_deck=slide_deck
        )

        print(
            "[SLIDE CONTENT REVISER] "
            "Revision completed successfully."
        )

        return revised_deck

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Slide Content Reviser returned malformed JSON."
        ) from error

    except GeminiError:
        raise

    except Exception as error:
        print(
            "\n========== SLIDE CONTENT REVISER ERROR =========="
        )

        print(
            type(error).__name__
        )

        print(
            str(error)
        )

        print(
            "==================================================\n"
        )

        raise RuntimeError(
            f"Slide content revision failed: {error}"
        ) from error