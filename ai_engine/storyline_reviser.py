import json
import re

from ai_engine.gemini_client import (
    GeminiError,
    generate_json,
)


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


REQUIRED_SLIDE_FIELDS = {
    "slide_number",
    "role",
    "purpose",
    "core_message",
    "concepts_used",
    "transition_to_next"
}
ALLOWED_SLIDE_ROLES = {
    "opening",
    "define",
    "explain_mechanism",
    "classify",
    "compare",
    "trace_evolution",
    "analyze_application",
    "examine_limitations",
    "evaluate",
    "connect_concepts",
    "synthesis"
}


def _extract_json(text: str) -> dict:
    cleaned = re.sub(
        r"^```(?:json)?|```$",
        "",
        text.strip(),
        flags=re.MULTILINE
    ).strip()

    return json.loads(cleaned)


def _validate_reviser_input(
    topic_analysis: dict,
    storyline: dict,
    critique: dict
) -> None:

    if not isinstance(topic_analysis, dict):
        raise TypeError(
            "topic_analysis must be a dictionary."
        )

    if not isinstance(storyline, dict):
        raise TypeError(
            "storyline must be a dictionary."
        )

    if not isinstance(critique, dict):
        raise TypeError(
            "critique must be a dictionary."
        )

    required_analysis_fields = [
        "topic",
        "core_question"
    ]

    missing_analysis_fields = [
        field
        for field in required_analysis_fields
        if field not in topic_analysis
    ]

    if missing_analysis_fields:
        raise ValueError(
            "Storyline Reviser received incomplete "
            "topic analysis. "
            f"Missing fields: {missing_analysis_fields}"
        )

    required_storyline_fields = [
        "topic",
        "total_slides",
        "narrative_thesis",
        "story_arc",
        "slides"
    ]

    missing_storyline_fields = [
        field
        for field in required_storyline_fields
        if field not in storyline
    ]

    if missing_storyline_fields:
        raise ValueError(
            "Storyline Reviser received incomplete storyline. "
            f"Missing fields: {missing_storyline_fields}"
        )

    if (
        isinstance(storyline["total_slides"], bool)
        or not isinstance(
            storyline["total_slides"],
            int
        )
    ):
        raise TypeError(
            "storyline total_slides must be an integer."
        )

    if storyline["total_slides"] < 3:
        raise ValueError(
            "Storyline must contain at least 3 total slides."
        )

    if not isinstance(
        storyline["slides"],
        list
    ):
        raise TypeError(
            "storyline slides must be a list."
        )

    if (
        len(storyline["slides"])
        != storyline["total_slides"]
    ):
        raise ValueError(
            "Input storyline slide count is inconsistent. "
            f"Expected {storyline['total_slides']}, "
            f"received {len(storyline['slides'])}."
        )

    required_critique_fields = [
        "decision",
        "issues",
        "banned_phrases_detected",
        "claims_needing_qualification",
        "revision_priority"
    ]

    missing_critique_fields = [
        field
        for field in required_critique_fields
        if field not in critique
    ]

    if missing_critique_fields:
        raise ValueError(
            "Storyline Reviser received incomplete critique. "
            f"Missing fields: {missing_critique_fields}"
        )

    critique_list_fields = [
        "issues",
        "banned_phrases_detected",
        "claims_needing_qualification",
        "revision_priority"
    ]

    for field in critique_list_fields:
        if not isinstance(
            critique[field],
            list
        ):
            raise TypeError(
                f"critique {field} must be a list."
            )


def _validate_revised_storyline(
    revised_storyline: dict,
    original_storyline: dict
) -> None:

    required_fields = [
        "topic",
        "total_slides",
        "narrative_thesis",
        "story_arc",
        "revision_summary",
        "slides"
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in revised_storyline
    ]

    if missing_fields:
        raise RuntimeError(
            "Storyline Reviser returned invalid JSON. "
            f"Missing fields: {missing_fields}"
        )

    original_topic = original_storyline["topic"]
    revised_topic = revised_storyline["topic"]

    if revised_topic != original_topic:
        raise RuntimeError(
            "Storyline Reviser changed the presentation topic. "
            f"Expected '{original_topic}', "
            f"received '{revised_topic}'."
        )

    total_slides = original_storyline["total_slides"]

    if revised_storyline["total_slides"] != total_slides:
        raise RuntimeError(
            "Storyline Reviser changed total_slides. "
            f"Expected {total_slides}, "
            f"received {revised_storyline['total_slides']}."
        )

    if not isinstance(
        revised_storyline["revision_summary"],
        list
    ):
        raise RuntimeError(
            "revision_summary must be a list."
        )

    slides = revised_storyline["slides"]

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
        if isinstance(slide, dict)
        else None
        for slide in slides
    ]

    if actual_numbers != expected_numbers:
        raise RuntimeError(
            "Storyline Reviser returned invalid numbering. "
            f"Expected {expected_numbers}, "
            f"received {actual_numbers}."
        )

    for slide in slides:

        if not isinstance(slide, dict):
            raise RuntimeError(
                "Every revised slide must be an object."
            )

        missing_slide_fields = (
            REQUIRED_SLIDE_FIELDS
            - set(slide.keys())
        )

        if missing_slide_fields:
            raise RuntimeError(
                "Storyline Reviser returned an incomplete slide. "
                f"Slide {slide.get('slide_number')} "
                f"is missing fields: "
                f"{sorted(missing_slide_fields)}"
            )

        if slide["role"] not in ALLOWED_SLIDE_ROLES:
            raise RuntimeError(
                "Storyline Reviser returned an invalid slide role. "
                f"Slide {slide['slide_number']} "
                f"has role '{slide['role']}'."
            )

        if not isinstance(
            slide["concepts_used"],
            list
        ):
            raise RuntimeError(
                "concepts_used must be a list on "
                f"slide {slide['slide_number']}."
            )

        text_fields = [
            "role",
            "purpose",
            "core_message"
        ]

        for field in text_fields:

            value = slide[field]

            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise RuntimeError(
                    f"{field} must be a non-empty string "
                    f"on slide {slide['slide_number']}."
                )

        transition_to_next = slide[
            "transition_to_next"
        ]

        if not isinstance(
            transition_to_next,
            str
        ):
            raise RuntimeError(
                "transition_to_next must be a string "
                f"on slide {slide['slide_number']}."
            )

        if (
            slide["slide_number"] < total_slides
            and not transition_to_next.strip()
        ):
            raise RuntimeError(
                "transition_to_next must be a non-empty string "
                f"on slide {slide['slide_number']}."
            )

    if slides[0]["role"] != "opening":
        raise RuntimeError(
            "Revised Slide 1 must have role 'opening'."
        )

    if slides[-1]["role"] != "synthesis":
        raise RuntimeError(
            f"Revised Slide {total_slides} "
            "must have role 'synthesis'."
        )

def revise_storyline(
    topic_analysis: dict,
    storyline: dict,
    critique: dict
) -> dict:

    _validate_reviser_input(
        topic_analysis,
        storyline,
        critique
    )

    total_slides = storyline["total_slides"]

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

17. Preserve the exact top-level topic value from the current storyline.

18. Every slide except the final synthesis slide must have a non-empty transition_to_next.

19. The final synthesis slide may use an empty string for transition_to_next because no slide follows it.
"""

    try:
        print(
            "[STORYLINE REVISER] Revising storyline..."
        )

        response_text = generate_json(
            system_prompt=STORYLINE_REVISER_PROMPT,
            user_prompt=user_prompt,
            temperature=0.15,
            max_output_tokens=4000,
            caller_name="STORYLINE REVISER"
        )

        revised_storyline = _extract_json(
            response_text
        )

        _validate_revised_storyline(
            revised_storyline,
            storyline
        )

        print(
            "[STORYLINE REVISER] "
            "Revision completed successfully."
        )

        return revised_storyline

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Storyline Reviser returned malformed JSON."
        ) from error

    except GeminiError:
        raise

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