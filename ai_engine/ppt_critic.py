import json
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

MODEL = "gemini-3.5-flash"


CRITIC_SYSTEM_PROMPT = """
You are the Quality Critic of a specialized AI presentation system.

Your job is to evaluate presentation planning output critically.

You are NOT a supportive assistant.
You do NOT praise weak work.
You do NOT rewrite the presentation unless explicitly requested.

You inspect whether the presentation is:

- relevant to the user's topic
- logically connected
- specific rather than generic
- technically careful
- appropriate for the audience
- free from unsupported claims
- free from unnecessary topic drift
- free from repetitive slide purposes

You must detect generic presentation language.

Examples include:

unlock potential
embrace the future
game changer
revolutionary journey
navigating the future
the opportunity
road ahead
transforming tomorrow
future starts now
power of innovation

You must also detect technically overconfident wording.

Examples:

- treating debated definitions as universally settled facts
- using "all", "always", "never", or "entirely" without justification
- reducing a broad technical field to one mechanism
- presenting theoretical categories as universally agreed taxonomies
- implying causal relationships without evidence

Evaluate the supplied Topic Analysis and Storyline together.

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


def critique_storyline(
    topic_analysis: dict,
    storyline: dict
) -> dict:

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from .env file."
        )

    client = genai.Client(
        api_key=api_key
    )

    analysis_json = json.dumps(
        topic_analysis,
        indent=2
    )

    storyline_json = json.dumps(
        storyline,
        indent=2
    )

    user_prompt = f"""
Evaluate this presentation storyline.

TOPIC ANALYSIS:

{analysis_json}

STORYLINE:

{storyline_json}

Return JSON matching exactly this structure:

{{
  "overall_score": 0,
  "decision": "APPROVE | REVISE | REJECT",

  "dimension_scores": {{
    "topic_relevance": 0,
    "narrative_flow": 0,
    "specificity": 0,
    "technical_care": 0,
    "audience_fit": 0,
    "non_generic_language": 0
  }},

  "strengths": [
    "specific strength"
  ],

  "issues": [
    {{
      "severity": "low | medium | high",
      "slide_number": 1,
      "category": "topic_drift | generic_language | technical_accuracy | unsupported_claim | repetition | narrative_gap | audience_mismatch",
      "problem": "precise description of the problem",
      "why_it_matters": "why this weakens the presentation",
      "revision_instruction": "specific instruction for correcting the problem"
    }}
  ],

  "banned_phrases_detected": [
    {{
      "phrase": "detected phrase",
      "slide_number": 1
    }}
  ],

  "claims_needing_qualification": [
    {{
      "claim": "exact or closely paraphrased claim",
      "slide_number": 1,
      "reason": "why the claim needs more careful wording"
    }}
  ],

  "duplicate_functions": [
    {{
      "slides": [2, 3],
      "reason": "why these slides perform the same intellectual function"
    }}
  ],

  "revision_priority": [
    "highest priority correction",
    "second priority correction"
  ]
}}

SCORING RULES:

- Every dimension is scored from 0 to 10.
- overall_score is scored from 0 to 10.

DECISION RULES:

APPROVE:
overall_score >= 8
AND no high severity issues
AND no banned phrases detected

REVISE:
overall_score >= 5
but improvements are required

REJECT:
overall_score < 5
or major topic drift makes the storyline unsuitable

IMPORTANT:

- Be strict.
- Do not reward polished wording if the content is inaccurate.
- Do not assume a claim is correct because it sounds technical.
- Detect banned phrases even when capitalization differs.
- Examine every slide.
- A synthesis slide may summarize earlier concepts without being marked as repetitive.
- Do not invent new factual problems merely to criticize something.
"""

    try:
        print(
            "[PPT CRITIC] Evaluating storyline..."
        )

        max_retries = 4
        response = None

        for attempt in range(
            1,
            max_retries + 1
        ):
            try:
                print(
                    f"[PPT CRITIC] API attempt "
                    f"{attempt}/{max_retries}"
                )

                response = client.models.generate_content(
                    model=MODEL,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=CRITIC_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.1,
                        max_output_tokens=3500
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
                    "[PPT CRITIC] "
                    f"Temporary Gemini error. "
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)

        if response is None:
            raise RuntimeError(
                "PPT Critic did not receive a response."
            )

        if not response.text:
            raise RuntimeError(
                "PPT Critic returned an empty response."
            )

        critique = _extract_json(
            response.text
        )

        required_fields = [
            "overall_score",
            "decision",
            "dimension_scores",
            "strengths",
            "issues",
            "banned_phrases_detected",
            "claims_needing_qualification",
            "duplicate_functions",
            "revision_priority"
        ]

        missing_fields = [
            field
            for field in required_fields
            if field not in critique
        ]

        if missing_fields:
            raise RuntimeError(
                "PPT Critic returned invalid JSON. "
                f"Missing fields: {missing_fields}"
            )

        valid_decisions = {
            "APPROVE",
            "REVISE",
            "REJECT"
        }

        if critique["decision"] not in valid_decisions:
            raise RuntimeError(
                "PPT Critic returned invalid decision: "
                f"{critique['decision']}"
            )

        print(
            "[PPT CRITIC] "
            f"Score: {critique['overall_score']}/10"
        )

        print(
            "[PPT CRITIC] "
            f"Decision: {critique['decision']}"
        )

        return critique

    except Exception as error:
        print(
            "\n========== PPT CRITIC ERROR =========="
        )

        print(
            type(error).__name__
        )

        print(
            str(error)
        )

        print(
            "======================================\n"
        )

        raise RuntimeError(
            f"Storyline critique failed: {error}"
        ) from error