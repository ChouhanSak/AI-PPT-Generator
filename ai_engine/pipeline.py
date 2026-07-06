from ai_engine.topic_analyzer import analyze_topic
from ai_engine.storyline_planner import plan_storyline
from ai_engine.ppt_critic import critique_storyline
from ai_engine.storyline_reviser import revise_storyline


MAX_REVISION_ROUNDS = 3


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


def run_storyline_pipeline(
    title: str,
    total_slides: int,
    audience: str = "",
    tone: str = "confident and clear"
) -> dict:

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

    for round_number in range(
        1,
        MAX_REVISION_ROUNDS + 1
    ):

        print(
            "\n----------------------------------------"
        )

        print(
            f"QUALITY ROUND {round_number}"
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

        score = critique.get(
            "overall_score",
            0
        )

        decision = critique.get(
            "decision"
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

            return {
                "status": "ACCEPTED",
                "topic_analysis": topic_analysis,
                "storyline": storyline,
                "final_critique": critique,
                "critique_history": critique_history,
                "revision_rounds": round_number - 1
            }

        if decision == "REJECT":

            print(
                "[PIPELINE] Storyline rejected."
            )

            print(
                "[PIPELINE] Generating a fresh storyline..."
            )

            storyline = plan_storyline(
                topic_analysis=topic_analysis,
                total_slides=total_slides
            )

            continue

        if round_number == MAX_REVISION_ROUNDS:

            print(
                "[PIPELINE] Maximum quality rounds reached."
            )

            break

        print(
            "[PIPELINE] Storyline requires revision."
        )

        storyline = revise_storyline(
            topic_analysis=topic_analysis,
            storyline=storyline,
            critique=critique
        )

    final_critique = critique_history[-1]

    return {
        "status": "MAX_ROUNDS_REACHED",
        "topic_analysis": topic_analysis,
        "storyline": storyline,
        "final_critique": final_critique,
        "critique_history": critique_history,
        "revision_rounds": MAX_REVISION_ROUNDS - 1
    }