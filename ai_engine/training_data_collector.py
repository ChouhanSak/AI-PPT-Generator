import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


TRAINING_DATA_DIR = Path(
    os.environ.get(
        "TRAINING_DATA_DIR",
        "training_data"
    )
)

QUALITY_TRACE_FILE = (
    TRAINING_DATA_DIR
    / "quality_traces.jsonl"
)

VALID_DATA_SOURCES = {
    "development",
    "test",
    "production"
}

def _validate_trace_input(
    stage: str,
    topic_analysis: dict,
    input_artifact: dict,
    critique: dict,
    output_artifact: dict | None
) -> None:

    if (
        not isinstance(stage, str)
        or not stage.strip()
    ):
        raise ValueError(
            "stage must be a non-empty string."
        )

    dictionary_fields = {
        "topic_analysis": topic_analysis,
        "input_artifact": input_artifact,
        "critique": critique
    }

    for (
        field_name,
        field_value
    ) in dictionary_fields.items():

        if not isinstance(
            field_value,
            dict
        ):
            raise TypeError(
                f"{field_name} must be a dictionary."
            )

    if (
        output_artifact is not None
        and not isinstance(
            output_artifact,
            dict
        )
    ):
        raise TypeError(
            "output_artifact must be a dictionary "
            "or None."
        )


def _build_quality_trace(
    *,
    stage: str,
    topic_analysis: dict,
    input_artifact: dict,
    critique: dict,
    output_artifact: dict | None,
    data_source: str
) -> dict:
    if data_source not in VALID_DATA_SOURCES:
        raise ValueError(
            "Unsupported training data source: "
            f"{data_source}"
        )
    decision = critique.get(
        "decision"
    )

    score = critique.get(
        "overall_score"
    )

    return {
    "trace_id": str(
        uuid4()
    ),
    "created_at": datetime.now(
        timezone.utc
    ).isoformat(),
    "stage": stage.strip(),
    "data_source": data_source,
    "topic": topic_analysis.get(
        "topic"
    ),
    "topic_analysis": topic_analysis,
    "input_artifact": input_artifact,
    "critique": critique,
    "output_artifact": output_artifact,
    "quality_signal": {
        "decision": decision,
        "score": score,
        "has_revision": (
            output_artifact is not None
        )
    }
}


def save_quality_trace(
    stage: str,
    topic_analysis: dict,
    input_artifact: dict,
    critique: dict,
    output_artifact: dict | None,
    data_source: str = "development"
) -> dict:

    _validate_trace_input(
        stage=stage,
        topic_analysis=topic_analysis,
        input_artifact=input_artifact,
        critique=critique,
        output_artifact=output_artifact
    )

    trace = _build_quality_trace(
        stage=stage,
        topic_analysis=topic_analysis,
        input_artifact=input_artifact,
        critique=critique,
        output_artifact=output_artifact,
        data_source=data_source
    )

    TRAINING_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with QUALITY_TRACE_FILE.open(
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            json.dumps(
                trace,
                ensure_ascii=False
            )
        )

        file.write(
            "\n"
        )

    print(
        "[TRAINING DATA] "
        f"Saved {stage} quality trace."
    )

    return trace