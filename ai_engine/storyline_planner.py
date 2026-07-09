import json
import re

from ai_engine.gemini_client import (
    GeminiError,
    generate_json,
)


STORYLINE_PLANNER_PROMPT = """
You are the Storyline Planner of a specialized AI presentation system.

You receive a structured topic analysis created by a Topic Analyzer.

Your responsibility is to create the intellectual narrative of the presentation.

You do NOT design slides.
You do NOT choose colors.
You do NOT choose visual layouts.
You do NOT write final presentation bullets.

Your job is to decide:

- what each slide must accomplish
- what the audience should understand after each slide
- how one idea logically leads to the next
- which concepts deserve priority
- how the presentation reaches a meaningful synthesis

A presentation is NOT a collection of independent facts.

It must behave like a connected explanation.

BAD STORYLINE:

Introduction
Overview
Benefits
Challenges
Future
Conclusion

BAD STORYLINE:

The Opportunity
Unlocking Potential
Embracing Change
The Road Ahead

These structures are generic and can apply to almost any topic.

GOOD STORYLINES are specific to the subject.

For Artificial Intelligence, a possible conceptual progression is:

What intelligence means in machines
→ How systems learn patterns from data
→ Different technical approaches to AI
→ Where those approaches are applied
→ What current systems cannot reliably do
→ What understanding AI requires from society

Do not copy this example mechanically.

Build the progression from the supplied topic analysis.

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


def _validate_topic_analysis_input(
    topic_analysis: dict
) -> None:

    if not isinstance(
        topic_analysis,
        dict
    ):
        raise TypeError(
            "topic_analysis must be a dictionary."
        )

    required_fields = [
        "topic",
        "presentation_goal",
        "core_question",
        "core_concepts"
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in topic_analysis
    ]

    if missing_fields:
        raise ValueError(
            "Storyline Planner received incomplete "
            "topic analysis. "
            f"Missing fields: {missing_fields}"
        )

    if not isinstance(
        topic_analysis["core_concepts"],
        list
    ):
        raise TypeError(
            "topic_analysis core_concepts "
            "must be a list."
        )


def _validate_storyline(
    storyline: dict,
    total_slides: int
) -> None:

    required_fields = [
        "topic",
        "total_slides",
        "narrative_thesis",
        "story_arc",
        "slides"
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in storyline
    ]

    if missing_fields:
        raise RuntimeError(
            "Storyline Planner returned invalid JSON. "
            f"Missing fields: {missing_fields}"
        )

    if storyline["total_slides"] != total_slides:
        raise RuntimeError(
            "Storyline metadata violated slide count. "
            f"Expected {total_slides}, "
            f"received {storyline['total_slides']}."
        )

    slides = storyline["slides"]

    if not isinstance(
        slides,
        list
    ):
        raise RuntimeError(
            "Storyline Planner returned invalid slides."
        )

    if len(slides) != total_slides:
        raise RuntimeError(
            "Storyline Planner violated slide count. "
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
            "Storyline Planner returned invalid "
            "slide numbering. "
            f"Expected {expected_numbers}, "
            f"received {actual_numbers}."
        )

    for slide in slides:
        required_slide_fields = [
        "slide_number",
        "role",
        "purpose",
        "core_message",
        "concepts_used",
    ]

        if slide["slide_number"] != total_slides:
            required_slide_fields.append(
                "transition_to_next"
        )

        missing_slide_fields = [
            field
            for field in required_slide_fields
            if field not in slide
        ]

        if missing_slide_fields:
            raise RuntimeError(
                "Storyline slide "
                f"{slide.get('slide_number')} "
                "is incomplete. "
                f"Missing fields: {missing_slide_fields}"
            )

        if not isinstance(
            slide["concepts_used"],
            list
        ):
            raise RuntimeError(
                "concepts_used must be a list on "
                f"slide {slide['slide_number']}."
            )

        if not isinstance(
            slide["core_message"],
            str
        ) or not slide["core_message"].strip():
            raise RuntimeError(
                "Every slide must contain a core message. "
                f"Slide {slide['slide_number']} is empty."
            )

        if slide["slide_number"] == total_slides:
            slide.setdefault(
                "transition_to_next",
                ""
            )

        if slides[0]["role"] != "opening":
            raise RuntimeError(
                "Slide 1 must have the opening role."
            )

        if slides[-1]["role"] != "synthesis":
            raise RuntimeError(
                f"Slide {total_slides} must have "
                "the synthesis role."
            )


def plan_storyline(
    topic_analysis: dict,
    total_slides: int
) -> dict:

    if not isinstance(
        total_slides,
        int
    ):
        raise TypeError(
            "total_slides must be an integer."
        )

    if total_slides < 3:
        raise ValueError(
            "A presentation must contain "
            "at least 3 total slides."
        )

    _validate_topic_analysis_input(
        topic_analysis
    )

    topic_json = json.dumps(
        topic_analysis,
        indent=2
    )

    user_prompt = f"""
Create the storyline for this presentation.

TOTAL SLIDES:
{total_slides}

IMPORTANT:

The requested number is the TOTAL number of slides.

The presentation must contain EXACTLY {total_slides} slides.

Slide 1 is the opening/title slide.

Slide {total_slides} is the final synthesis or conclusion slide.

Therefore you must create exactly {total_slides - 2} middle content slides.

TOPIC ANALYSIS:

{topic_json}

Return JSON matching exactly this structure:

{{
  "topic": "presentation topic",

  "total_slides": {total_slides},

  "narrative_thesis": "one sentence describing the central intellectual argument of the presentation",

  "story_arc": "one concise description of how the presentation progresses",

  "slides": [
    {{
      "slide_number": 1,
      "role": "opening",
      "purpose": "what the opening must establish",
      "core_message": "the single idea the audience should receive",
      "concepts_used": [],
      "transition_to_next": "why the audience logically needs the next slide"
    }}
  ]
}}

RULES:

1. Return exactly {total_slides} slide objects.

2. Slide numbers must start at 1 and end at {total_slides}.

3. Slide 1 role must be "opening".

4. Slide {total_slides} role must be "synthesis".

5. Middle slide roles must describe intellectual function.

Examples:

"define"
"explain_mechanism"
"classify"
"compare"
"trace_evolution"
"analyze_application"
"examine_limitations"
"evaluate"
"connect_concepts"

6. Every slide must have ONE core message.

7. The core message must be topic-specific.

8. Avoid generic headings or motivational language.

9. Do not write final bullet points.

10. Do not select layouts.

11. Do not invent statistics.

12. Use concepts from the Topic Analyzer.

13. Do not introduce a business or investor perspective unless present in the topic analysis.

14. Slides 1 through {total_slides - 1} must include transition_to_next
    explaining the logical need for the following slide.

    The final synthesis slide has no following slide, so its
    transition_to_next must be an empty string "".

15. The final slide must synthesize the presentation rather than simply say "Thank You".

16. The storyline must answer the Topic Analyzer's core_question.

17. No two slides may perform the same intellectual function unless genuinely necessary.
"""

    try:
        print(
            "[STORYLINE PLANNER] Building narrative..."
        )

        response_text = generate_json(
            system_prompt=STORYLINE_PLANNER_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_output_tokens=3500,
            caller_name="STORYLINE PLANNER"
        )

        storyline = _extract_json(
            response_text
        )

        _validate_storyline(
            storyline,
            total_slides
        )

        print(
            "[STORYLINE PLANNER] "
            f"Created exactly "
            f"{len(storyline['slides'])} slides."
        )

        return storyline

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Storyline Planner returned malformed JSON."
        ) from error

    except GeminiError:
        raise

    except Exception as error:
        print(
            "\n========== STORYLINE PLANNER ERROR =========="
        )

        print(
            type(error).__name__
        )

        print(
            str(error)
        )

        print(
            "================================================\n"
        )

        raise RuntimeError(
            f"Storyline planning failed: {error}"
        ) from error