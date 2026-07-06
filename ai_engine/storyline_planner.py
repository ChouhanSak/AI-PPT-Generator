import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


MODEL = "gemini-3.5-flash"


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


def plan_storyline(
    topic_analysis: dict,
    total_slides: int
) -> dict:

    if total_slides < 3:
        raise ValueError(
            "A presentation must contain at least 3 total slides."
        )

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from .env file."
        )

    client = genai.Client(
        api_key=api_key
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

14. Every transition_to_next must explain the logical need for the following slide.

15. The final slide must synthesize the presentation rather than simply say "Thank You".

16. The storyline must answer the Topic Analyzer's core_question.

17. No two slides may perform the same intellectual function unless genuinely necessary.
"""

    try:

        print(
            "[STORYLINE PLANNER] Building narrative..."
        )

        response = client.models.generate_content(
            model=MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=STORYLINE_PLANNER_PROMPT,
                response_mime_type="application/json",
                temperature=0.3,
                max_output_tokens=3500
            )
        )

        if not response.text:
            raise RuntimeError(
                "Storyline Planner returned an empty response."
            )

        storyline = _extract_json(
            response.text
        )

        slides = storyline.get(
            "slides"
        )

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
                f"Expected {total_slides}, received {len(slides)}."
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
                "Storyline Planner returned invalid slide numbering. "
                f"Expected {expected_numbers}, received {actual_numbers}."
            )

        if slides[0].get("role") != "opening":
            raise RuntimeError(
                "Slide 1 must have the opening role."
            )

        if slides[-1].get("role") != "synthesis":
            raise RuntimeError(
                f"Slide {total_slides} must have the synthesis role."
            )

        print(
            "[STORYLINE PLANNER] "
            f"Created exactly {len(slides)} slides."
        )

        return storyline

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