import json
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

MODEL = "gemini-3.5-flash"


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


def analyze_topic(
    title: str,
    audience: str = "",
    tone: str = "confident and clear"
) -> dict:

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from .env file."
        )

    client = genai.Client(
        api_key=api_key
    )

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

        max_retries = 4
        response = None

        for attempt in range(
            1,
            max_retries + 1
        ):
            try:
                print(
                    f"[TOPIC ANALYZER] API attempt "
                    f"{attempt}/{max_retries}"
                )

                response = client.models.generate_content(
                    model=MODEL,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=TOPIC_ANALYZER_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.2,
                        max_output_tokens=2500
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
                    "[TOPIC ANALYZER] "
                    f"Temporary Gemini error. "
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)

        if response is None:
            raise RuntimeError(
                "Topic Analyzer did not receive a response."
            )

        if not response.text:
            raise RuntimeError(
                "Topic Analyzer returned an empty response."
            )

        analysis = _extract_json(
            response.text
        )

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
            analysis["core_concepts"],
            list
        ):
            raise RuntimeError(
                "core_concepts must be a list."
            )

        print(
            "[TOPIC ANALYZER] "
            "Analysis completed successfully."
        )

        return analysis

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