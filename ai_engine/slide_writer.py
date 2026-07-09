import json
import re

from ai_engine.gemini_client import (
    GeminiError,
    generate_json,
)


SLIDE_WRITER_SYSTEM_PROMPT = """
You are the Slide Writer of a specialized AI presentation system.

You receive:

1. A structured Topic Analysis.
2. An approved Presentation Storyline.

Your responsibility is to convert the approved narrative plan into concise,
audience-facing presentation content.

You do NOT redesign the storyline.
You do NOT change the number of slides.
You do NOT choose visual layouts.
You do NOT choose colors, fonts, icons, or images.
You do NOT invent statistics, quotations, studies, or sources.

The Storyline Planner decides WHAT each slide must communicate.

You decide HOW that approved idea should be expressed clearly on the slide.

Every slide must preserve its original:
- slide number
- role
- conceptual purpose
- core message

Presentation content must be concise.

Avoid:
- paragraphs disguised as bullet points
- generic motivational language
- repeated bullets
- vague topic labels
- unnecessary jargon
- unsupported absolute claims
- writing the same idea in the key message and every bullet

A bullet should communicate a meaningful supporting idea.

BAD BULLETS:

- Machine Learning
- Data
- Algorithms
- Future of AI

GOOD BULLETS:

- Training examples expose recurring patterns
- Model parameters adjust during optimization
- Learned patterns guide predictions on new inputs

The key message is the single takeaway of the slide.

The bullets support that takeaway.

Return ONLY valid JSON.
"""


ALLOWED_CONTENT_TYPES = {
    "opening",
    "explanation",
    "process",
    "classification",
    "comparison",
    "timeline",
    "application",
    "limitations",
    "evaluation",
    "synthesis",
}


def _extract_json(
    text: str
) -> dict:

    cleaned = re.sub(
        r"^```(?:json)?|```$",
        "",
        text.strip(),
        flags=re.MULTILINE
    ).strip()

    return json.loads(
        cleaned
    )


def _validate_writer_input(
    topic_analysis: dict,
    storyline: dict
) -> None:

    if not isinstance(
        topic_analysis,
        dict
    ):
        raise TypeError(
            "topic_analysis must be a dictionary."
        )

    if not isinstance(
        storyline,
        dict
    ):
        raise TypeError(
            "storyline must be a dictionary."
        )

    required_analysis_fields = [
        "topic",
        "presentation_goal",
        "audience",
        "core_question",
    ]

    missing_analysis_fields = [
        field
        for field in required_analysis_fields
        if field not in topic_analysis
    ]

    if missing_analysis_fields:
        raise ValueError(
            "Slide Writer received incomplete topic analysis. "
            f"Missing fields: {missing_analysis_fields}"
        )

    required_storyline_fields = [
        "topic",
        "total_slides",
        "narrative_thesis",
        "story_arc",
        "slides",
    ]

    missing_storyline_fields = [
        field
        for field in required_storyline_fields
        if field not in storyline
    ]

    if missing_storyline_fields:
        raise ValueError(
            "Slide Writer received incomplete storyline. "
            f"Missing fields: {missing_storyline_fields}"
        )

    if not isinstance(
        storyline["slides"],
        list
    ):
        raise TypeError(
            "storyline slides must be a list."
        )

    if not storyline["slides"]:
        raise ValueError(
            "storyline must contain slides."
        )


def _validate_slide_content(
    slide: dict,
    expected_slide: dict
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
            "Slide Writer returned an incomplete slide. "
            f"Missing fields: {missing_fields}"
        )

    expected_number = expected_slide.get(
        "slide_number"
    )

    if slide["slide_number"] != expected_number:
        raise RuntimeError(
            "Slide Writer changed slide numbering. "
            f"Expected {expected_number}, "
            f"received {slide['slide_number']}."
        )

    expected_role = expected_slide.get(
        "role"
    )

    if slide["role"] != expected_role:
        raise RuntimeError(
            "Slide Writer changed the slide role. "
            f"Slide {expected_number} expected "
            f"'{expected_role}', received '{slide['role']}'."
        )

    if slide["content_type"] not in ALLOWED_CONTENT_TYPES:
        raise RuntimeError(
            "Slide Writer returned unsupported content_type. "
            f"Slide {expected_number}: "
            f"'{slide['content_type']}'."
        )

    text_fields = [
        "title",
        "subtitle",
        "key_message",
        "speaker_context",
    ]

    for field in text_fields:

        if not isinstance(
            slide[field],
            str
        ):
            raise RuntimeError(
                f"Slide {expected_number} field "
                f"'{field}' must be a string."
            )

    if not slide["title"].strip():
        raise RuntimeError(
            f"Slide {expected_number} title cannot be empty."
        )

    if not slide["key_message"].strip():
        raise RuntimeError(
            f"Slide {expected_number} "
            "key_message cannot be empty."
        )

    bullets = slide["bullets"]

    if not isinstance(
        bullets,
        list
    ):
        raise RuntimeError(
            f"Slide {expected_number} bullets must be a list."
        )
    if len(slide["bullets"]) > 4:
        raise RuntimeError(
            f"Slide {slide['slide_number']} contains too many bullets. "
            "A slide may contain at most 4 bullets."
        )

    for bullet in bullets:

        if not isinstance(
            bullet,
            str
        ):
            raise RuntimeError(
                f"Slide {expected_number} "
                "contains a non-string bullet."
            )

        if not bullet.strip():
            raise RuntimeError(
                f"Slide {expected_number} "
                "contains an empty bullet."
            )

    normalized_bullets = [
        bullet.strip().lower()
        for bullet in bullets
    ]

    if len(
        normalized_bullets
    ) != len(
        set(normalized_bullets)
    ):
        raise RuntimeError(
            f"Slide {expected_number} "
            "contains duplicate bullets."
        )


def _validate_slide_deck(
    slide_deck: dict,
    storyline: dict
) -> None:

    required_fields = [
        "topic",
        "total_slides",
        "slides",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in slide_deck
    ]

    if missing_fields:
        raise RuntimeError(
            "Slide Writer returned invalid JSON. "
            f"Missing fields: {missing_fields}"
        )

    expected_total = storyline[
        "total_slides"
    ]

    if slide_deck["total_slides"] != expected_total:
        raise RuntimeError(
            "Slide Writer changed total slide count. "
            f"Expected {expected_total}, "
            f"received {slide_deck['total_slides']}."
        )

    slides = slide_deck["slides"]

    if not isinstance(
        slides,
        list
    ):
        raise RuntimeError(
            "Slide Writer output slides must be a list."
        )

    if len(slides) != expected_total:
        raise RuntimeError(
            "Slide Writer violated slide count. "
            f"Expected {expected_total}, "
            f"received {len(slides)}."
        )

    expected_slides = storyline[
        "slides"
    ]

    for slide, expected_slide in zip(
        slides,
        expected_slides
    ):
        _validate_slide_content(
            slide=slide,
            expected_slide=expected_slide
        )


def write_slides(
    topic_analysis: dict,
    storyline: dict
) -> dict:

    _validate_writer_input(
        topic_analysis=topic_analysis,
        storyline=storyline
    )

    topic_json = json.dumps(
        topic_analysis,
        indent=2
    )

    storyline_json = json.dumps(
        storyline,
        indent=2
    )

    total_slides = storyline[
        "total_slides"
    ]

    user_prompt = f"""
Write presentation-ready content for the approved storyline.

TOPIC ANALYSIS:

{topic_json}

APPROVED STORYLINE:

{storyline_json}

The output must contain EXACTLY {total_slides} slides.

Return JSON matching exactly this structure:

{{
  "topic": "presentation topic",
  "total_slides": {total_slides},
  "slides": [
    {{
      "slide_number": 1,
      "role": "opening",
      "title": "concise audience-facing slide title",
      "subtitle": "optional concise subtitle or empty string",
      "content_type": "opening | explanation | process | classification | comparison | timeline | application | limitations | evaluation | synthesis",
      "key_message": "one concise audience-facing takeaway",
      "bullets": [
        "meaningful supporting point"
      ],
      "speaker_context": "brief context explaining what the presenter should emphasize"
    }}
  ]
}}

CONTENT RULES:

1. Return exactly {total_slides} slides.

2. Preserve every slide_number exactly.

3. Preserve every storyline role exactly.

4. Do not change the approved conceptual progression.

5. Each title must be concise and topic-specific.

6. Each key_message must express exactly one primary takeaway.

7. Bullets must support the key_message.

8. Use 0 to 4 bullets per slide.

9. Opening slides should normally use 0 bullets.

10. Synthesis slides may use up to 4 bullets.

11. Each bullet should express one meaningful idea.

12. Avoid bullet fragments that are only topic labels.

13. Do not repeat identical bullets.

14. Do not invent statistics.

15. Do not invent quotations.

16. Do not invent sources or research studies.

17. Do not add visual or layout instructions.

18. speaker_context is presenter guidance, not slide-visible copy.

19. Keep slide-visible content concise.

20. Preserve the intellectual meaning of each storyline core_message.
"""

    try:

        print(
            "[SLIDE WRITER] Writing slide content..."
        )

        response_text = generate_json(
            system_prompt=SLIDE_WRITER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.25,
            max_output_tokens=5000,
            caller_name="SLIDE WRITER"
        )

        slide_deck = _extract_json(
            response_text
        )

        _validate_slide_deck(
            slide_deck=slide_deck,
            storyline=storyline
        )

        print(
            "[SLIDE WRITER] "
            f"Created content for "
            f"{len(slide_deck['slides'])} slides."
        )

        return slide_deck

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "Slide Writer returned malformed JSON."
        ) from error

    except GeminiError:
        raise

    except Exception as error:

        print(
            "\n========== SLIDE WRITER ERROR =========="
        )

        print(
            type(error).__name__
        )

        print(
            str(error)
        )

        print(
            "========================================\n"
        )

        raise RuntimeError(
            f"Slide writing failed: {error}"
        ) from error