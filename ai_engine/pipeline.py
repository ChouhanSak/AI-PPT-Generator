from ai_engine.topic_analyzer import analyze_topic
from ai_engine.storyline_planner import plan_storyline
from ai_engine.ppt_critic import critique_storyline
from ai_engine.storyline_reviser import revise_storyline
from ai_engine.slide_writer import write_slides
from ai_engine.visual_director import direct_visuals
from ai_engine.slide_content_critic import (
    critique_slide_content,
)

from ai_engine.slide_content_reviser import (
    revise_slide_content,
)
from ai_engine.training_data_collector import (
    save_quality_trace,
)

from ai_engine.pipeline_cache import (
    load_pipeline_cache,
    save_pipeline_cache,
)

MAX_REVISION_ROUNDS = 3
MAX_REGENERATION_ROUNDS = 2
MAX_CONTENT_REVISION_ROUNDS = 3

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

            save_quality_trace(
                stage="storyline",
                topic_analysis=topic_analysis,
                input_artifact=storyline,
                critique=critique,
                output_artifact=None
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

            original_storyline = storyline

            revised_storyline = revise_storyline(
                topic_analysis=topic_analysis,
                storyline=original_storyline,
                critique=critique
            )

            save_quality_trace(
                stage="storyline",
                topic_analysis=topic_analysis,
                input_artifact=original_storyline,
                critique=critique,
                output_artifact=revised_storyline
            )

            storyline = revised_storyline

            continue

        raise RuntimeError(
        "Pipeline reached an invalid state."
        )


def _has_high_content_issues(
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


def _has_content_banned_phrases(
    critique: dict
) -> bool:

    banned_phrases = critique.get(
        "banned_phrases_detected",
        []
    )

    return len(banned_phrases) > 0


def _should_accept_slide_content(
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
        and not _has_high_content_issues(
            critique
        )
        and not _has_content_banned_phrases(
            critique
        )
    )


def run_slide_content_pipeline(
    topic_analysis: dict,
    storyline: dict
) -> dict:

    print(
        "\n========================================"
    )

    print(
        "SLIDE CONTENT QUALITY PIPELINE"
    )

    print(
        "========================================\n"
    )

    slide_deck = write_slides(
        topic_analysis=topic_analysis,
        storyline=storyline
    )

    critique_history = []

    revision_rounds = 0

    while True:

        round_number = len(
            critique_history
        ) + 1

        print(
            "\n----------------------------------------"
        )

        print(
            f"CONTENT QUALITY ROUND {round_number}"
        )

        print(
            "----------------------------------------"
        )

        critique = critique_slide_content(
            topic_analysis=topic_analysis,
            storyline=storyline,
            slide_deck=slide_deck
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
            f"[CONTENT PIPELINE] Score: {score}/10"
        )

        print(
            f"[CONTENT PIPELINE] Decision: {decision}"
        )

        if _should_accept_slide_content(
            critique
        ):

            print(
                "[CONTENT PIPELINE] "
                "Slide content accepted."
            )

            save_quality_trace(
                stage="slide_content",
                topic_analysis=topic_analysis,
                input_artifact=slide_deck,
                critique=critique,
                output_artifact=None
            )

            return {
                "status": "ACCEPTED",
                "slide_deck": slide_deck,
                "final_critique": critique,
                "critique_history": critique_history,
                "revision_rounds": revision_rounds
            }

        if decision == "REJECT":

            print(
                "[CONTENT PIPELINE] "
                "Slide content rejected."
            )

            return {
                "status": "REJECTED",
                "slide_deck": slide_deck,
                "final_critique": critique,
                "critique_history": critique_history,
                "revision_rounds": revision_rounds
            }

        if decision != "REVISE":
            raise RuntimeError(
                "Content pipeline received an unsupported "
                f"critic decision: {decision}"
            )

        if (
            revision_rounds
            >= MAX_CONTENT_REVISION_ROUNDS
        ):

            print(
                "[CONTENT PIPELINE] "
                "Maximum content revision rounds reached."
            )

            return {
                "status": "MAX_REVISIONS_REACHED",
                "slide_deck": slide_deck,
                "final_critique": critique,
                "critique_history": critique_history,
                "revision_rounds": revision_rounds
            }

        print(
            "[CONTENT PIPELINE] "
            "Slide content requires revision."
        )

        revision_rounds += 1

        print(
            "[CONTENT PIPELINE] "
            f"Revision {revision_rounds}/"
            f"{MAX_CONTENT_REVISION_ROUNDS}"
        )

        original_slide_deck = slide_deck

        revised_slide_deck = revise_slide_content(
            topic_analysis=topic_analysis,
            storyline=storyline,
            slide_deck=original_slide_deck,
            critique=critique
        )

        save_quality_trace(
            stage="slide_content",
            topic_analysis=topic_analysis,
            input_artifact=original_slide_deck,
            critique=critique,
            output_artifact=revised_slide_deck
        )

        slide_deck = revised_slide_deck

    
def run_generation_pipeline(
    title: str,
    total_slides: int,
    audience: str = "",
    tone: str = "confident and clear"
) -> dict:

    print(
        "\n========================================"
    )

    print(
        "FULL PRESENTATION GENERATION PIPELINE"
    )

    print(
        "========================================\n"
    )

    storyline_result = load_pipeline_cache(
        title=title,
        total_slides=total_slides,
        audience=audience,
        tone=tone,
        stage="storyline_result"
    )

    if storyline_result is None:

        storyline_result = run_storyline_pipeline(
            title=title,
            total_slides=total_slides,
            audience=audience,
            tone=tone
        )

        storyline_status = storyline_result.get(
            "status"
        )

        if storyline_status != "ACCEPTED":

            raise RuntimeError(
                "Presentation generation stopped because "
                "the storyline was not accepted. "
                f"Pipeline status: {storyline_status}"
            )

        save_pipeline_cache(
            title=title,
            total_slides=total_slides,
            audience=audience,
            tone=tone,
            stage="storyline_result",
            data=storyline_result
        )

    else:

        print(
            "[GENERATION PIPELINE] "
            "Using cached accepted storyline."
        )

    storyline_status = storyline_result.get(
        "status"
    )

    if storyline_status != "ACCEPTED":

        raise RuntimeError(
            "Cached storyline is not accepted. "
            f"Pipeline status: {storyline_status}"
        )

    topic_analysis = storyline_result[
        "topic_analysis"
    ]

    storyline = storyline_result[
        "storyline"
    ]

    print(
        "[GENERATION PIPELINE] "
        "Preparing slide content quality pipeline..."
    )

    content_result = load_pipeline_cache(
        title=title,
        total_slides=total_slides,
        audience=audience,
        tone=tone,
        stage="content_result"
    )

    if content_result is None:

        content_result = run_slide_content_pipeline(
            topic_analysis=topic_analysis,
            storyline=storyline
        )

        content_status = content_result.get(
            "status"
        )

        if content_status != "ACCEPTED":

            raise RuntimeError(
                "Presentation generation stopped because "
                "slide content was not accepted. "
                f"Content pipeline status: {content_status}"
            )

        save_pipeline_cache(
            title=title,
            total_slides=total_slides,
            audience=audience,
            tone=tone,
            stage="content_result",
            data=content_result
        )

    else:

        print(
            "[GENERATION PIPELINE] "
            "Using cached accepted slide content."
        )

    content_status = content_result.get(
        "status"
    )

    if content_status != "ACCEPTED":

        raise RuntimeError(
            "Cached slide content is not accepted. "
            f"Content pipeline status: {content_status}"
        )

    slide_deck = content_result[
        "slide_deck"
    ]

    print(
        "[GENERATION PIPELINE] "
        "Preparing slide visual plan..."
    )

    visual_plan = load_pipeline_cache(
        title=title,
        total_slides=total_slides,
        audience=audience,
        tone=tone,
        stage="visual_plan"
    )

    if visual_plan is None:

        visual_plan = direct_visuals(
            topic_analysis=topic_analysis,
            storyline=storyline,
            slide_deck=slide_deck
        )

        save_pipeline_cache(
            title=title,
            total_slides=total_slides,
            audience=audience,
            tone=tone,
            stage="visual_plan",
            data=visual_plan
        )

    else:

        print(
            "[GENERATION PIPELINE] "
            "Using cached visual plan."
        )

    print(
        "[GENERATION PIPELINE] "
        "Generation package completed."
    )

    return {
        "status": "GENERATION_PACKAGE_READY",
        "topic_analysis": topic_analysis,
        "storyline": storyline,
        "slide_deck": slide_deck,
        "visual_plan": visual_plan,
        "final_critique": storyline_result[
            "final_critique"
        ],
        "critique_history": storyline_result[
            "critique_history"
        ],
        "revision_rounds": storyline_result[
            "revision_rounds"
        ],
        "regeneration_rounds": storyline_result[
            "regeneration_rounds"
        ],
        "content_critique": content_result[
            "final_critique"
        ],
        "content_critique_history": content_result[
            "critique_history"
        ],
        "content_revision_rounds": content_result[
            "revision_rounds"
        ]
    }