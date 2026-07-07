from ai_engine.topic_analyzer import analyze_topic
from ai_engine.storyline_planner import plan_storyline
from ai_engine.ppt_critic import critique_storyline
from ai_engine.storyline_reviser import revise_storyline


MAX_REVISION_ROUNDS = 3
MAX_REGENERATION_ROUNDS = 2


VALID_CRITIC_DECISIONS = {
    "APPROVE",
    "REVISE",
    "REJECT"
}


def _validate_pipeline_input(
    title: str,
    total_slides: int,
    audience: str,
    tone: str
) -> None:

    if (
        not isinstance(title, str)
        or not title.strip()
    ):
        raise ValueError(
            "Presentation title must be a non-empty string."
        )

    if (
        isinstance(total_slides, bool)
        or not isinstance(total_slides, int)
    ):
        raise TypeError(
            "total_slides must be an integer."
        )

    if total_slides < 3:
        raise ValueError(
            "A presentation must contain at least 3 total slides."
        )

    if not isinstance(audience, str):
        raise TypeError(
            "audience must be a string."
        )

    if not isinstance(tone, str):
        raise TypeError(
            "tone must be a string."
        )

    if not tone.strip():
        raise ValueError(
            "tone must be a non-empty string."
        )


def _has_high_severity_issues(
    critique: dict
) -> bool:

    issues = critique.get(
        "issues",
        []
    )

    return any(
        issue.get("severity") == "high"
        for issue in issues
    )


def _has_banned_phrases(
    critique: dict
) -> bool:

    banned_phrases = critique.get(
        "banned_phrases_detected",
        []
    )

    return len(banned_phrases) > 0


def _should_accept(
    critique: dict
) -> bool:

    decision = critique.get(
        "decision"
    )

    score = critique.get(
        "overall_score",
        0
    )

    return (
        decision == "APPROVE"
        and score >= 8
        and not _has_high_severity_issues(
            critique
        )
        and not _has_banned_phrases(
            critique
        )
    )


def _validate_critic_decision(
    critique: dict
) -> str:

    decision = critique.get(
        "decision"
    )

    if decision not in VALID_CRITIC_DECISIONS:
        raise RuntimeError(
            "Pipeline received an unsupported "
            f"critic decision: {decision}"
        )

    return decision


def _build_pipeline_result(
    *,
    status: str,
    topic_analysis: dict,
    storyline: dict,
    final_critique: dict,
    critique_history: list,
    revision_count: int,
    regeneration_count: int
) -> dict:

    return {
        "status": status,
        "topic_analysis": topic_analysis,
        "storyline": storyline,
        "final_critique": final_critique,
        "critique_history": critique_history,
        "revision_rounds": revision_count,
        "regeneration_rounds": regeneration_count
    }


def run_storyline_pipeline(
    title: str,
    total_slides: int,
    audience: str = "",
    tone: str = "confident and clear"
) -> dict:

    _validate_pipeline_input(
        title,
        total_slides,
        audience,
        tone
    )

    title = title.strip()
    tone = tone.strip()

    print(
        "\n========================================"
    )

    print(
        "PPT INTELLIGENCE PIPELINE"
    )

    print(
        "========================================"
    )

    print(
        f"Topic: {title}"
    )

    print(
        f"Total Slides: {total_slides}"
    )

    print(
        "========================================\n"
    )

    topic_analysis = analyze_topic(
        title=title,
        audience=audience,
        tone=tone
    )

    storyline = plan_storyline(
        topic_analysis=topic_analysis,
        total_slides=total_slides
    )

    critique_history = []

    revision_count = 0
    regeneration_count = 0
    quality_round = 0

    while True:

        quality_round += 1

        print(
            "\n----------------------------------------"
        )

        print(
            f"QUALITY ROUND {quality_round}"
        )

        print(
            "----------------------------------------"
        )

        critique = critique_storyline(
            topic_analysis=topic_analysis,
            storyline=storyline
        )

        critique_history.append(
            critique
        )

        decision = _validate_critic_decision(
            critique
        )

        score = critique.get(
            "overall_score",
            0
        )

        print(
            f"[PIPELINE] Score: {score}/10"
        )

        print(
            f"[PIPELINE] Decision: {decision}"
        )

        if _should_accept(
            critique
        ):

            print(
                "[PIPELINE] Storyline accepted."
            )

            return _build_pipeline_result(
                status="ACCEPTED",
                topic_analysis=topic_analysis,
                storyline=storyline,
                final_critique=critique,
                critique_history=critique_history,
                revision_count=revision_count,
                regeneration_count=regeneration_count
            )

        if decision == "REJECT":

            if (
                regeneration_count
                >= MAX_REGENERATION_ROUNDS
            ):

                print(
                    "[PIPELINE] "
                    "Maximum regeneration rounds reached."
                )

                return _build_pipeline_result(
                    status="REJECTED",
                    topic_analysis=topic_analysis,
                    storyline=storyline,
                    final_critique=critique,
                    critique_history=critique_history,
                    revision_count=revision_count,
                    regeneration_count=regeneration_count
                )

            regeneration_count += 1

            print(
                "[PIPELINE] Storyline rejected."
            )

            print(
                "[PIPELINE] "
                "Generating a fresh storyline..."
            )

            storyline = plan_storyline(
                topic_analysis=topic_analysis,
                total_slides=total_slides
            )

            continue

        if decision == "REVISE":

            if (
                revision_count
                >= MAX_REVISION_ROUNDS
            ):

                print(
                    "[PIPELINE] "
                    "Maximum revision rounds reached."
                )

                return _build_pipeline_result(
                    status="MAX_REVISIONS_REACHED",
                    topic_analysis=topic_analysis,
                    storyline=storyline,
                    final_critique=critique,
                    critique_history=critique_history,
                    revision_count=revision_count,
                    regeneration_count=regeneration_count
                )

            revision_count += 1

            print(
                "[PIPELINE] Storyline requires revision."
            )

            print(
                "[PIPELINE] "
                f"Revision {revision_count}/"
                f"{MAX_REVISION_ROUNDS}"
            )

            storyline = revise_storyline(
                topic_analysis=topic_analysis,
                storyline=storyline,
                critique=critique
            )

            continue

        raise RuntimeError(
            "Pipeline reached an invalid state."
        )