import json
import re

from ai_engine.gemini_client import (
    GeminiError,
    generate_json,
)


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


VALID_DECISIONS = {
    "APPROVE",
    "REVISE",
    "REJECT"
}


VALID_SEVERITIES = {
    "low",
    "medium",
    "high"
}


VALID_ISSUE_CATEGORIES = {
    "topic_drift",
    "generic_language",
    "technical_accuracy",
    "unsupported_claim",
    "repetition",
    "narrative_gap",
    "audience_mismatch"
}


REQUIRED_DIMENSIONS = {
    "topic_relevance",
    "narrative_flow",
    "specificity",
    "technical_care",
    "audience_fit",
    "non_generic_language"
}


def _extract_json(text: str) -> dict:
    cleaned = re.sub(
        r"^```(?:json)?|```$",
        "",
        text.strip(),
        flags=re.MULTILINE
    ).strip()

    return json.loads(cleaned)


def _validate_critic_input(
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
        "core_question"
    ]

    missing_analysis_fields = [
        field
        for field in required_analysis_fields
        if field not in topic_analysis
    ]

    if missing_analysis_fields:
        raise ValueError(
            "PPT Critic received incomplete topic analysis. "
            f"Missing fields: {missing_analysis_fields}"
        )

    required_storyline_fields = [
        "topic",
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
            "PPT Critic received incomplete storyline. "
            f"Missing fields: {missing_storyline_fields}"
        )

    if not isinstance(
        storyline["slides"],
        list
    ):
        raise TypeError(
            "storyline slides must be a list."
        )


def _validate_score(
    score,
    field_name: str
) -> None:

    if isinstance(score, bool) or not isinstance(
        score,
        (int, float)
    ):
        raise RuntimeError(
            f"{field_name} must be a numeric score."
        )

    if not 0 <= score <= 10:
        raise RuntimeError(
            f"{field_name} must be between 0 and 10."
        )


def _validate_critique(
    critique: dict
) -> None:

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

    _validate_score(
        critique["overall_score"],
        "overall_score"
    )

    if critique["decision"] not in VALID_DECISIONS:
        raise RuntimeError(
            "PPT Critic returned invalid decision: "
            f"{critique['decision']}"
        )

    if not isinstance(
        critique["dimension_scores"],
        dict
    ):
        raise RuntimeError(
            "dimension_scores must be an object."
        )

    actual_dimensions = set(
        critique["dimension_scores"].keys()
    )

    missing_dimensions = (
        REQUIRED_DIMENSIONS - actual_dimensions
    )

    if missing_dimensions:
        raise RuntimeError(
            "PPT Critic returned incomplete "
            "dimension scores. "
            f"Missing dimensions: "
            f"{sorted(missing_dimensions)}"
        )

    for dimension in REQUIRED_DIMENSIONS:
        _validate_score(
            critique["dimension_scores"][dimension],
            f"dimension_scores.{dimension}"
        )

    list_fields = [
        "strengths",
        "issues",
        "banned_phrases_detected",
        "claims_needing_qualification",
        "duplicate_functions",
        "revision_priority"
    ]

    for field in list_fields:
        if not isinstance(
            critique[field],
            list
        ):
            raise RuntimeError(
                f"{field} must be a list."
            )

    for issue in critique["issues"]:
        if not isinstance(
            issue,
            dict
        ):
            raise RuntimeError(
                "Every critic issue must be an object."
            )

        required_issue_fields = [
            "severity",
            "slide_number",
            "category",
            "problem",
            "why_it_matters",
            "revision_instruction"
        ]

        missing_issue_fields = [
            field
            for field in required_issue_fields
            if field not in issue
        ]

        if missing_issue_fields:
            raise RuntimeError(
                "PPT Critic returned an incomplete issue. "
                f"Missing fields: {missing_issue_fields}"
            )

        if issue["severity"] not in VALID_SEVERITIES:
            raise RuntimeError(
                "PPT Critic returned invalid severity: "
                f"{issue['severity']}"
            )

        if (
            issue["category"]
            not in VALID_ISSUE_CATEGORIES
        ):
            raise RuntimeError(
                "PPT Critic returned invalid issue category: "
                f"{issue['category']}"
            )

    _validate_decision_consistency(
        critique
    )

def _validate_decision_consistency(
    critique: dict
) -> None:

    score = critique["overall_score"]
    decision = critique["decision"]

    has_high_severity_issue = any(
        issue["severity"] == "high"
        for issue in critique["issues"]
    )

    has_banned_phrases = bool(
        critique["banned_phrases_detected"]
    )

    has_major_topic_drift = any(
        issue["severity"] == "high"
        and issue["category"] == "topic_drift"
        for issue in critique["issues"]
    )

    if decision == "APPROVE":
        if (
            score < 8
            or has_high_severity_issue
            or has_banned_phrases
        ):
            raise RuntimeError(
                "PPT Critic returned an inconsistent "
                "APPROVE decision."
            )

    elif decision == "REJECT":
        if (
            score >= 5
            and not has_major_topic_drift
        ):
            raise RuntimeError(
                "PPT Critic returned an inconsistent "
                "REJECT decision."
            )

    elif decision == "REVISE":
        if (
            score < 5
            or has_major_topic_drift
        ):
            raise RuntimeError(
                "PPT Critic returned an inconsistent "
                "REVISE decision."
            )


def critique_storyline(
    topic_analysis: dict,
    storyline: dict
) -> dict:

    _validate_critic_input(
        topic_analysis,
        storyline
    )

    analysis_json = json.dumps(
        topic_analysis,
        indent=2
    )

    storyline_json = json.dumps(
        storyline,
        indent=2
    )

    total_slides = storyline.get(
        "total_slides",
        len(
            storyline.get(
                "slides",
                []
            )
        )
    )

    user_prompt = f"""
Evaluate this presentation storyline.

TOPIC ANALYSIS:

{analysis_json}

STORYLINE:

{storyline_json}

PRESENTATION CONSTRAINT:

The user explicitly requested exactly {total_slides} slides.

You MUST evaluate the storyline relative to this slide budget.

A short presentation is NOT expected to cover every core concept from
the topic analysis.

For a 3 to 4 slide presentation:
- prioritize the central question
- preserve a clear beginning, explanation, and synthesis
- allow selective coverage of only the most essential concepts
- do not penalize omitted secondary concepts merely because the topic is broad

For a 5 to 7 slide presentation:
- expect moderate conceptual coverage
- prioritize major mechanisms, stages, or categories
- minor omissions should normally lead to REVISE, not REJECT

For an 8 to 12 slide presentation:
- expect broader conceptual coverage
- important unexplained gaps may reduce the score more significantly

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
- Judge conceptual quality relative to the requested {total_slides}-slide budget.
- Do not lower the score simply because a short deck cannot cover every core concept.
- Missing secondary concepts are not automatically narrative gaps.
- Evaluate whether the selected concepts form the strongest possible explanation within the available slide count.

DECISION RULES:

APPROVE:
overall_score >= 8
AND no high severity issues
AND no banned phrases detected

REVISE:
overall_score >= 5
AND the storyline is fundamentally usable
but targeted improvements are required

REJECT:
overall_score < 5 ONLY when the storyline is fundamentally unsuitable

REJECT should normally be reserved for:
- major topic drift
- severe factual or conceptual framing failure
- storyline that does not answer the central topic
- incoherent narrative progression
- content aimed at the wrong presentation domain

IMPORTANT:

- Limited slide count alone is NEVER a reason to REJECT.
- Omission of secondary concepts alone is NEVER a reason to REJECT.
- Prefer REVISE over REJECT when specific corrections can repair the storyline.
- Do not demand comprehensive topic coverage from a 3-slide deck.
- Be strict about accuracy, relevance, and narrative logic.
- Do not reward polished wording if the content is inaccurate.
- Do not assume a claim is correct because it sounds technical.
- Detect banned phrases even when capitalization differs.
- Examine every slide.
- A synthesis slide may summarize earlier concepts without being marked as repetitive.
- Do not invent factual problems merely to criticize something.
"""

    try:
        print(
            "[PPT CRITIC] Evaluating storyline..."
        )

        response_text = generate_json(
            system_prompt=CRITIC_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            max_output_tokens=3500,
            caller_name="PPT CRITIC"
        )

        critique = _extract_json(
            response_text
        )

        _validate_critique(
            critique
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

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "PPT Critic returned malformed JSON."
        ) from error

    except GeminiError:
        raise

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