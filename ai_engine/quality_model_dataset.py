import json
import os
from pathlib import Path


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

QUALITY_MODEL_DATASET_FILE = (
    TRAINING_DATA_DIR
    / "quality_model_dataset.jsonl"
)


VALID_DECISIONS = {
    "APPROVE",
    "REVISE"
}


LABEL_MAP = {
    "APPROVE": 0,
    "REVISE": 1
}


def _load_quality_traces() -> list[dict]:

    if not QUALITY_TRACE_FILE.exists():
        raise FileNotFoundError(
            "Quality trace file does not exist."
        )

    traces = []

    with QUALITY_TRACE_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1
        ):

            line = line.strip()

            if not line:
                continue

            try:
                trace = json.loads(
                    line
                )

            except json.JSONDecodeError as error:
                raise RuntimeError(
                    "Invalid JSON in quality trace file "
                    f"at line {line_number}."
                ) from error

            traces.append(
                trace
            )

    return traces


def _is_quality_model_candidate(
    trace: dict
) -> bool:

    if trace.get("data_source") == "test":
        return False

    decision = trace.get(
        "quality_signal",
        {}
    ).get(
        "decision"
    )

    if decision not in VALID_DECISIONS:
        return False

    artifact = trace.get(
        "input_artifact"
    )

    if (
        not isinstance(artifact, dict)
        or not artifact
    ):
        return False

    return True


def _serialize_artifact(
    trace: dict
) -> str:

    artifact = trace.get(
        "input_artifact",
        {}
    )

    topic_analysis = trace.get(
        "topic_analysis",
        {}
    )

    payload = {
        "topic_analysis": topic_analysis,
        "artifact": artifact
    }

    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False
    )


def _build_quality_example(
    trace: dict
) -> dict:

    quality_signal = trace.get(
        "quality_signal",
        {}
    )

    decision = quality_signal.get(
        "decision"
    )

    return {
        "example_id": trace.get(
            "trace_id"
        ),
        "stage": trace.get(
            "stage"
        ),
        "topic": trace.get(
            "topic"
        ),
        "text": _serialize_artifact(
            trace
        ),
        "label": LABEL_MAP[
            decision
        ],
        "decision": decision,
        "critic_score": quality_signal.get(
            "score"
        ),
        "data_source": trace.get(
            "data_source"
        )
    }


def build_quality_model_dataset() -> list[dict]:

    print(
        "[QUALITY MODEL DATASET] "
        "Loading quality traces..."
    )

    traces = _load_quality_traces()

    examples = []

    seen_example_ids = set()

    for trace in traces:

        if not _is_quality_model_candidate(
            trace
        ):
            continue

        example = _build_quality_example(
            trace
        )

        example_id = example.get(
            "example_id"
        )

        if example_id in seen_example_ids:
            continue

        seen_example_ids.add(
            example_id
        )

        examples.append(
            example
        )

    TRAINING_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with QUALITY_MODEL_DATASET_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        for example in examples:

            file.write(
                json.dumps(
                    example,
                    ensure_ascii=False
                )
            )

            file.write(
                "\n"
            )

    approve_count = sum(
        example["label"] == 0
        for example in examples
    )

    revise_count = sum(
        example["label"] == 1
        for example in examples
    )

    print(
        "[QUALITY MODEL DATASET] "
        f"Created {len(examples)} examples."
    )

    print(
        "[QUALITY MODEL DATASET] "
        f"APPROVE examples: {approve_count}"
    )

    print(
        "[QUALITY MODEL DATASET] "
        f"REVISE examples: {revise_count}"
    )

    return examples