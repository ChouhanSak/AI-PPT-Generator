import json
import re

from ai_engine.gemini_client import (
    GeminiError,
    generate_json,
)


SLIDE_CONTENT_CRITIC_PROMPT = """
You are the Slide Content Critic of a specialized AI presentation system.

You receive:

1. A structured Topic Analysis
2. An approved Presentation Storyline
3. A written Slide Deck

The storyline has already passed narrative quality control.

Your responsibility is to evaluate whether the Slide Writer converted that
approved storyline into strong presentation content without weakening,
distorting, or genericizing the narrative.

You are NOT evaluating visual design.

You do NOT choose layouts.
You do NOT choose colors.
You do NOT recommend images.
You do NOT rewrite slides.

Evaluate the written slide content for:

- fidelity to the approved storyline
- topic relevance
- title specificity
- bullet quality
- concise presentation writing
- unsupported or overconfident claims
- generic or motivational language
- repetition between slides
- excessive text density
- preservation of the intended core message

Generic presentation language includes phrases such as:

- unlock potential
- embrace the future
- game changer
- revolutionary journey
- navigating the future
- the opportunity
- road ahead
- transforming tomorrow
- future starts now
- power of innovation

A slide may use different wording from the storyline.

Different wording is acceptable when the intellectual meaning is preserved.

Do not punish concise presentation language merely because it is shorter
than the storyline.

Return ONLY valid JSON.
"""


ALLOWED_DECISIONS = {
    "APPROVE",
    "REVISE",
    "REJECT",
}


ALLOWED_SEVERITIES = {
    "low",
    "medium",
    "high",
}


ALLOWED_CATEGORIES = {
    "storyline_drift",
    "generic_language",
    "unsupported_claim",
    "technical_accuracy",
    "repetition",
    "text_density",
    "weak_title",
    "weak_bullets",
    "core_message_loss",
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


def _validate_score(
    score,
    field_name: str
) -> None:

    if isinstance(
        score,
        bool
    ) or not isinstance(
        score,
        (int, float)
    ):
        raise RuntimeError(
            f"{field_name} must be numeric."
        )

    if not 0 <= score <= 10:
        raise RuntimeError(
            f"{field_name} must be between 0 and 10."
        )


def _validate_content_critique(
    critique: dict,
    slide_deck: dict
) -> None:

    required_fields = [
        "overall_score",
        "decision",
        "dimension_scores",
        "strengths",
        "issues",
        "banned_phrases_detected",
        "claims_needing_qualification",
        "duplicate_content",
        "revision_priority",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in critique
    ]

    if missing_fields:
        raise RuntimeError(
            "Slide Content Critic returned invalid JSON. "
            f"Missing fields: {missing_fields}"
        )

    _validate_score(
        critique["overall_score"],
        "overall_score"
    )

    decision = critique["decision"]

    if decision not in ALLOWED_DECISIONS:
        raise RuntimeError(
            "Slide Content Critic returned invalid decision: "
            f"{decision}"
        )

    dimension_scores = critique[
        "dimension_scores"
    ]

    if not isinstance(
        dimension_scores,
        dict
    ):
        raise RuntimeError(
            "dimension_scores must be an object."
        )

    required_dimensions = [
        "storyline_fidelity",
        "topic_relevance",
        "title_specificity",
        "bullet_quality",
        "technical_care",
        "conciseness",
        "non_generic_language",
    ]

    missing_dimensions = [
        dimension
        for dimension in required_dimensions
        if dimension not in dimension_scores
    ]

    if missing_dimensions:
        raise RuntimeError(
            "Slide Content Critic returned incomplete "
            "dimension_scores. Missing dimensions: "
            f"{missing_dimensions}"
        )

    for (
        dimension,
        score
    ) in dimension_scores.items():

        _validate_score(
            score,
            f"dimension_scores.{dimension}"
        )

    list_fields = [
        "strengths",
        "issues",
        "banned_phrases_detected",
        "claims_needing_qualification",
        "duplicate_content",
        "revision_priority",
    ]

    for field in list_fields:

        if not isinstance(
            critique[field],
            list
        ):
            raise RuntimeError(
                f"{field} must be a list."
            )

    total_slides = slide_deck.get(
        "total_slides"
    )

    for issue in critique["issues"]:

        if not isinstance(
            issue,
            dict
        ):
            raise RuntimeError(
                "Each content issue must be an object."
            )

        required_issue_fields = [
            "severity",
            "slide_number",
            "category",
            "problem",
            "why_it_matters",
            "revision_instruction",
        ]

        missing_issue_fields = [
            field
            for field in required_issue_fields
            if field not in issue
        ]

        if missing_issue_fields:
            raise RuntimeError(
                "Slide Content Critic returned an "
                "incomplete issue. Missing fields: "
                f"{missing_issue_fields}"
            )

        if (
            issue["severity"]
            not in ALLOWED_SEVERITIES
        ):
            raise RuntimeError(
                "Slide Content Critic returned invalid "
                f"issue severity: {issue['severity']}"
            )

        if (
            issue["category"]
            not in ALLOWED_CATEGORIES
        ):
            raise RuntimeError(
                "Slide Content Critic returned invalid "
                f"issue category: {issue['category']}"
            )

        slide_number = issue[
            "slide_number"
        ]

        if (
            isinstance(
                slide_number,
                bool
            )
            or not isinstance(
                slide_number,
                int
            )
            or slide_number < 1
            or slide_number > total_slides
        ):
            raise RuntimeError(
                "Slide Content Critic referenced an "
                "invalid slide number: "
                f"{slide_number}"
            )


def critique_slide_content(
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

    user_prompt = f"""
Evaluate the written slide content.

TOPIC ANALYSIS:

{topic_json}

APPROVED STORYLINE:

{storyline_json}

WRITTEN SLIDE DECK:

{slide_deck_json}

Return JSON matching exactly this structure:

{{
  "overall_score": 0,

  "decision": "APPROVE | REVISE | REJECT",

  "dimension_scores": {{
    "storyline_fidelity": 0,
    "topic_relevance": 0,
    "title_specificity": 0,
    "bullet_quality": 0,
    "technical_care": 0,
    "conciseness": 0,
    "non_generic_language": 0
  }},

  "strengths": [
    "specific content strength"
  ],

  "issues": [
    {{
      "severity": "low | medium | high",
      "slide_number": 1,
      "category": "storyline_drift | generic_language | unsupported_claim | technical_accuracy | repetition | text_density | weak_title | weak_bullets | core_message_loss",
      "problem": "precise content problem",
      "why_it_matters": "why the problem weakens the slide",
      "revision_instruction": "specific correction instruction"
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
      "claim": "claim requiring careful wording",
      "slide_number": 1,
      "reason": "why qualification is needed"
    }}
  ],

  "duplicate_content": [
    {{
      "slides": [2, 3],
      "reason": "what content is unnecessarily repeated"
    }}
  ],

  "revision_priority": [
    "highest priority correction",
    "second priority correction"
  ]
}}

SCORING RULES:

- Every score is from 0 to 10.
- overall_score is from 0 to 10.

DECISION RULES:

APPROVE:
overall_score >= 8
AND no high severity issues
AND no banned phrases detected

REVISE:
overall_score >= 5
but written content needs correction

REJECT:
overall_score < 5
or the Slide Writer substantially abandoned the approved storyline

IMPORTANT:

- Examine every slide.
- Compare every slide with the corresponding approved storyline slide.
- Detect loss of the intended core message.
- Detect generic titles.
- Detect vague bullets.
- Detect unsupported absolute claims.
- Detect unnecessary repetition.
- Do not criticize visual design.
- Do not invent factual problems merely to create issues.
- Opening slides may contain fewer or no bullets.
- Synthesis slides may restate earlier concepts when genuinely synthesizing them.
"""

    try:

        print(
            "[SLIDE CONTENT CRITIC] "
            "Evaluating written slides..."
        )

        response_text = generate_json(
            system_prompt=SLIDE_CONTENT_CRITIC_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            max_output_tokens=4000,
            caller_name="SLIDE CONTENT CRITIC"
        )

        critique = _extract_json(
            response_text
        )

        _validate_content_critique(
            critique,
            slide_deck
        )

        print(
            "[SLIDE CONTENT CRITIC] "
            f"Score: {critique['overall_score']}/10"
        )

        print(
            "[SLIDE CONTENT CRITIC] "
            f"Decision: {critique['decision']}"
        )

        return critique

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "Slide Content Critic returned malformed JSON."
        ) from error

    except GeminiError:
        raise

    except Exception as error:

        print(
            "\n========== SLIDE CONTENT CRITIC ERROR =========="
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
            f"Slide content critique failed: {error}"
        ) from error