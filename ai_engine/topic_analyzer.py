import json
import re

from ai_engine.gemini_client import (
    GeminiError,
    generate_json,
)


TOPIC_ANALYZER_PROMPT = """
You are the Topic Analyzer of a specialized AI presentation system.

Your job is NOT to create slides.
Your job is NOT to write presentation bullets.
Your job is NOT to design the presentation.

Your only responsibility is to deeply understand the user's presentation topic.

Analyze:
1. What the topic actually means.
2. The academic or professional domain of the topic.
3. The likely presentation goal.
4. The appropriate depth for the target audience.
5. The real concepts, mechanisms, categories, stages, events, or arguments
   that must be covered to explain the topic correctly.
6. Possible topic drift that must be avoided.

Do not turn broad educational topics into:
- investment pitches
- corporate strategy decks
- motivational presentations
- sales presentations

unless the user explicitly asks for that perspective.

Avoid generic presentation language such as:
- unlock potential
- embrace the future
- game changer
- revolutionary journey
- the opportunity
- navigating the future

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


def _validate_topic_analysis(
    analysis: dict
) -> None:

    required_fields = [
        "topic",
        "normalized_topic",
        "domain",
        "topic_type",
        "presentation_goal",
        "audience",
        "core_question",
        "core_concepts",
        "recommended_story_direction",
        "avoid_topic_drift"
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in analysis
    ]

    if missing_fields:
        raise RuntimeError(
            "Topic Analyzer returned invalid JSON. "
            f"Missing fields: {missing_fields}"
        )

    if not isinstance(
        analysis["audience"],
        dict
    ):
        raise RuntimeError(
            "audience must be an object."
        )

    if not isinstance(
        analysis["core_concepts"],
        list
    ):
        raise RuntimeError(
            "core_concepts must be a list."
        )

    if not isinstance(
        analysis["recommended_story_direction"],
        list
    ):
        raise RuntimeError(
            "recommended_story_direction must be a list."
        )

    if not isinstance(
        analysis["avoid_topic_drift"],
        list
    ):
        raise RuntimeError(
            "avoid_topic_drift must be a list."
        )

    if not 5 <= len(
        analysis["core_concepts"]
    ) <= 10:
        raise RuntimeError(
            "core_concepts must contain between "
            "5 and 10 concepts."
        )


def analyze_topic(
    title: str,
    audience: str = "",
    tone: str = "confident and clear"
) -> dict:

    if not title or not title.strip():
        raise ValueError(
            "Presentation title cannot be empty."
        )

    title = title.strip()

    audience_text = (
        audience.strip()
        if audience and audience.strip()
        else "not specified"
    )

    user_prompt = f"""
Analyze this presentation request.

PRESENTATION TOPIC:
"{title}"

TARGET AUDIENCE:
{audience_text}

REQUESTED TONE:
{tone}

Return JSON matching exactly this structure:

{{
  "topic": "{title}",
  "normalized_topic": "clear canonical name of the topic",
  "domain": "main subject domain",
  "topic_type": "educational | explanatory | analytical | persuasive | historical | technical",
  "presentation_goal": "one precise sentence describing what the audience should understand",
  "audience": {{
    "specified": true,
    "description": "audience description",
    "assumed_knowledge": "beginner | intermediate | advanced",
    "content_depth": "introductory | moderate | deep"
  }},
  "core_question": "the central question the presentation must answer",
  "core_concepts": [
    {{
      "concept": "real topic concept",
      "importance": "why this concept is necessary"
    }}
  ],
  "recommended_story_direction": [
    "first conceptual direction",
    "second conceptual direction",
    "third conceptual direction"
  ],
  "avoid_topic_drift": [
    "unwanted direction",
    "unwanted direction"
  ],
  "content_warnings": [
    "possible accuracy or framing issue to watch"
  ]
}}

RULES:

- Identify 5 to 10 genuine core concepts.
- Core concepts must belong directly to the topic.
- Do not generate slide headings.
- Do not generate presentation bullets.
- Do not suggest layouts.
- Do not write marketing language.
- Do not invent statistics.
- Do not force a business perspective.
- If audience is not specified, assume a general learner.
- If the title is broad, explain the fundamental subject before applications.
- The presentation goal must be specific to the topic.
- recommended_story_direction must describe conceptual progression, not slide design.
"""

    try:
        print(
            f"[TOPIC ANALYZER] Analyzing: {title}"
        )

        response_text = generate_json(
            system_prompt=TOPIC_ANALYZER_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
            max_output_tokens=2500,
            caller_name="TOPIC ANALYZER"
        )

        analysis = _extract_json(
            response_text
        )

        _validate_topic_analysis(
            analysis
        )

        print(
            "[TOPIC ANALYZER] "
            "Analysis completed successfully."
        )

        return analysis

    except json.JSONDecodeError as error:
        raise RuntimeError(
        "Topic Analyzer returned malformed JSON."
    ) from error

    except GeminiError:
     raise

    except Exception as error:
        print(
        "\n========== TOPIC ANALYZER ERROR =========="
        )

        print(
        type(error).__name__
        )

        print(
            str(error)
        )

        print(
         "==========================================\n"
        )

        raise RuntimeError(
            f"Topic analysis failed: {error}"
        ) from error