import json
import re


from ai_engine.gemini_client import (
    GeminiError,
    generate_json,
)


VISUAL_DIRECTOR_PROMPT = """
You are the Visual Director of a specialized AI presentation system.

You receive:

1. A structured Topic Analysis.
2. An approved Presentation Storyline.
3. Written slide content.

Your responsibility is to decide how each slide should communicate its
existing idea visually.

You do NOT rewrite slide content.
You do NOT change slide titles.
You do NOT change slide roles.
You do NOT add new factual claims.
You do NOT change the number of slides.

Your job is to select an appropriate visual communication strategy.

Possible visual strategies include:

- typography-led opening
- structured text
- process flow
- comparison
- timeline
- hierarchy
- relationship diagram
- conceptual diagram
- data chart
- image-supported explanation
- synthesis framework

A visual must serve the slide's key message.

Do not add decorative images merely to fill space.

Prefer diagrams when relationships, mechanisms, stages, or structures
must be explained.

Prefer comparison structures when the slide contrasts categories,
approaches, or alternatives.

Prefer timelines only when chronological order is genuinely important.

Prefer charts only when the supplied slide content contains quantitative
information that can support a chart.

Never invent numbers for a chart.

visual_type MUST be one of:

opening_hero
diagram
flowchart
timeline
comparison
table
chart
concept_map
process
quote
image
summary

Never invent new visual types.
Return ONLY valid JSON.
"""


ALLOWED_VISUAL_TYPES = {
    "typography",
    "structured_text",
    "process_flow",
    "comparison",
    "timeline",
    "hierarchy",
    "relationship_diagram",
    "conceptual_diagram",
    "data_chart",
    "image_supported",
    "synthesis_framework",
}


ALLOWED_LAYOUTS = {
    "centered",
    "title_body",
    "two_column",
    "horizontal_flow",
    "vertical_flow",
    "timeline",
    "comparison_split",
    "diagram_focus",
    "chart_focus",
    "image_text_split",
    "framework",
}


ALLOWED_VISUAL_PRIORITIES = {
    "primary",
    "supporting",
    "minimal",
}


def _extract_json(text: str) -> dict:
    cleaned = re.sub(
        r"^```(?:json)?|```$",
        "",
        text.strip(),
        flags=re.MULTILINE
    ).strip()

    return json.loads(cleaned)


def _validate_visual_plan(
    visual_plan: dict,
    slide_deck: dict
) -> None:

    required_fields = [
        "topic",
        "total_slides",
        "slides",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in visual_plan
    ]

    if missing_fields:
        raise RuntimeError(
            "Visual Director returned invalid JSON. "
            f"Missing fields: {missing_fields}"
        )

    expected_total = slide_deck.get(
        "total_slides"
    )

    if visual_plan["total_slides"] != expected_total:
        raise RuntimeError(
            "Visual Director changed total_slides. "
            f"Expected {expected_total}, "
            f"received {visual_plan['total_slides']}."
        )

    slides = visual_plan["slides"]

    if not isinstance(
        slides,
        list
    ):
        raise RuntimeError(
            "Visual Director slides must be a list."
        )

    if len(slides) != expected_total:
        raise RuntimeError(
            "Visual Director violated slide count. "
            f"Expected {expected_total}, "
            f"received {len(slides)}."
        )

    expected_numbers = list(
        range(
            1,
            expected_total + 1
        )
    )

    actual_numbers = [
        slide.get("slide_number")
        for slide in slides
    ]

    if actual_numbers != expected_numbers:
        raise RuntimeError(
            "Visual Director returned invalid slide numbering. "
            f"Expected {expected_numbers}, "
            f"received {actual_numbers}."
        )

    for slide in slides:
        _normalize_visual_slide(
        slide
    )

    _validate_visual_slide(
        slide
    )

def _normalize_visual_slide(
    slide: dict
) -> dict:

    visual_type_aliases = {
        "opening_hero": "typography",
        "hero": "typography",
        "title_slide": "typography",
        "text": "structured_text",
        "bullet_list": "structured_text",
        "process": "process_flow",
        "flowchart": "process_flow",
        "comparison_chart": "comparison",
        "comparison_table": "comparison",
        "chronology": "timeline",
        "tree": "hierarchy",
        "relationship": "relationship_diagram",
        "diagram": "conceptual_diagram",
        "concept_diagram": "conceptual_diagram",
        "chart": "data_chart",
        "graph": "data_chart",
        "image": "image_supported",
        "image_with_text": "image_supported",
        "framework": "synthesis_framework",
        "summary_framework": "synthesis_framework",
    }

    layout_aliases = {
        "hero": "centered",
        "opening_hero": "centered",
        "center": "centered",
        "title": "title_body",
        "content": "title_body",
        "split": "two_column",
        "columns": "two_column",
        "process": "horizontal_flow",
        "flow": "horizontal_flow",
        "vertical": "vertical_flow",
        "timeline_layout": "timeline",
        "comparison": "comparison_split",
        "diagram": "diagram_focus",
        "chart": "chart_focus",
        "image": "image_text_split",
        "synthesis": "framework",
    }

    visual_type = slide.get(
        "visual_type"
    )

    layout = slide.get(
        "layout"
    )

    if visual_type in visual_type_aliases:
        print(
            "[VISUAL DIRECTOR] "
            f"Normalized visual_type "
            f"'{visual_type}' -> "
            f"'{visual_type_aliases[visual_type]}'."
        )

        slide["visual_type"] = (
            visual_type_aliases[
                visual_type
            ]
        )

    if layout in layout_aliases:
        print(
            "[VISUAL DIRECTOR] "
            f"Normalized layout "
            f"'{layout}' -> "
            f"'{layout_aliases[layout]}'."
        )

        slide["layout"] = (
            layout_aliases[
                layout
            ]
        )

    return slide


def _validate_visual_slide(
    slide: dict
) -> None:

    slide_number = slide.get(
        "slide_number"
    )

    required_fields = [
        "slide_number",
        "visual_type",
        "layout",
        "visual_priority",
        "visual_concept",
        "image_query",
        "chart_type",
        "diagram_nodes",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in slide
    ]

    if missing_fields:
        raise RuntimeError(
            f"Visual Director returned incomplete Slide "
            f"{slide_number}. Missing fields: {missing_fields}"
        )

    if slide["visual_type"] not in ALLOWED_VISUAL_TYPES:
        raise RuntimeError(
            "Visual Director returned unsupported visual_type. "
            f"Slide {slide_number}: "
            f"'{slide['visual_type']}'."
        )

    if slide["layout"] not in ALLOWED_LAYOUTS:
        raise RuntimeError(
            "Visual Director returned unsupported layout. "
            f"Slide {slide_number}: "
            f"'{slide['layout']}'."
        )

    if (
        slide["visual_priority"]
        not in ALLOWED_VISUAL_PRIORITIES
    ):
        raise RuntimeError(
            "Visual Director returned unsupported "
            "visual_priority. "
            f"Slide {slide_number}: "
            f"'{slide['visual_priority']}'."
        )

    text_fields = [
        "visual_concept",
        "image_query",
        "chart_type",
    ]

    for field in text_fields:
        if not isinstance(
            slide[field],
            str
        ):
            raise RuntimeError(
                f"Slide {slide_number} field "
                f"'{field}' must be a string."
            )

    if not slide["visual_concept"].strip():
        raise RuntimeError(
            f"Slide {slide_number} contains "
            "an empty visual_concept."
        )

    if not isinstance(
        slide["diagram_nodes"],
        list
    ):
        raise RuntimeError(
            f"Slide {slide_number} diagram_nodes "
            "must be a list."
        )

    for node in slide["diagram_nodes"]:
        if not isinstance(
            node,
            str
        ):
            raise RuntimeError(
                f"Slide {slide_number} contains "
                "a non-string diagram node."
            )

        if not node.strip():
            raise RuntimeError(
                f"Slide {slide_number} contains "
                "an empty diagram node."
            )

    if (
        slide["visual_type"] in {
            "process_flow",
            "hierarchy",
            "relationship_diagram",
            "conceptual_diagram",
            "synthesis_framework",
        }
        and not slide["diagram_nodes"]
    ):
        raise RuntimeError(
            f"Slide {slide_number} uses "
            f"{slide['visual_type']} but does not "
            "provide diagram_nodes."
        )
    if (
        slide["visual_type"] == "image_supported"
        and not slide["image_query"].strip()
    ):
        raise RuntimeError(
        f"Slide {slide_number} uses image_supported "
        "but does not provide image_query."
        )
    if (
        slide["visual_type"] == "data_chart"
        and not slide["chart_type"].strip()
    ):
        raise RuntimeError(
            f"Slide {slide_number} uses data_chart "
            "but does not specify chart_type."
        )

def direct_visuals(
    topic_analysis: dict,
    storyline: dict,
    slide_deck: dict
) -> dict:

    topic_json = json.dumps(
        topic_analysis,
        indent=2
    )

    storyline_json = json.dumps(
        storyline,
        indent=2
    )

    slide_deck_json = json.dumps(
        slide_deck,
        indent=2
    )

    total_slides = slide_deck.get(
        "total_slides"
    )

    user_prompt = f"""
Create a visual communication plan for this presentation.

TOPIC ANALYSIS:

{topic_json}

APPROVED STORYLINE:

{storyline_json}

WRITTEN SLIDE CONTENT:

{slide_deck_json}

The visual plan must contain EXACTLY {total_slides} slides.

Return JSON matching exactly this structure:

{{
  "topic": "presentation topic",
  "total_slides": {total_slides},
  "slides": [
    {{
      "slide_number": 1,
      "visual_type": "typography",
      "layout": "centered",
      "visual_priority": "minimal",
      "visual_concept": "precise description of the visual communication idea",
      "image_query": "",
      "chart_type": "",
      "diagram_nodes": []
    }}
  ]
}}

RULES:

1. Preserve the exact slide count.

2. Preserve slide numbering.

3. Do not rewrite titles, bullets, key messages, or roles.

4. visual_type MUST be exactly one of these values:

typography
structured_text
process_flow
comparison
timeline
hierarchy
relationship_diagram
conceptual_diagram
data_chart
image_supported
synthesis_framework

Never create a new visual_type.
Never use values such as opening_hero, hero, title_slide,
flowchart, diagram, chart, image, or framework.

5. layout MUST be exactly one of these values:

centered
title_body
two_column
horizontal_flow
vertical_flow
timeline
comparison_split
diagram_focus
chart_focus
image_text_split
framework

Never create a new layout value.

6. visual_priority must be primary, supporting, or minimal.

7. Use image_query only when an external explanatory image is useful.

8. Do not use image_query for decorative filler.

9. Use chart_type only when quantitative data already exists in the
   supplied slide content.

10. Never invent chart data.

11. Use diagram_nodes only when a diagram is genuinely useful.

12. diagram_nodes must contain short conceptual labels, not paragraphs.

13. Opening slides should usually use typography with minimal visual
   complexity.

14. Process or mechanism slides should prefer process_flow or
   conceptual_diagram.

15. Comparison slides should prefer comparison.

16. Synthesis slides should prefer synthesis_framework when appropriate.

17. Every visual_concept must explain how the visual supports the
   slide's existing key message.
"""

    try:
        print(
            "[VISUAL DIRECTOR] Planning visual strategy..."
        )

        response_text = generate_json(
            system_prompt=VISUAL_DIRECTOR_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
            max_output_tokens=4000,
            caller_name="VISUAL DIRECTOR"
        )

        visual_plan = _extract_json(
            response_text
        )

        _validate_visual_plan(
            visual_plan,
            slide_deck
        )

        print(
            "[VISUAL DIRECTOR] "
            "Visual strategy completed successfully."
        )

        return visual_plan

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Visual Director returned malformed JSON."
        ) from error

    except GeminiError:
        raise

    except Exception as error:
        print(
            "\n========== VISUAL DIRECTOR ERROR =========="
        )

        print(
            type(error).__name__
        )

        print(
            str(error)
        )

        print(
            "===========================================\n"
        )

        raise RuntimeError(
            f"Visual direction failed: {error}"
        ) from error