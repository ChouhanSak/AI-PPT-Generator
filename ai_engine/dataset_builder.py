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

TRAINING_EXAMPLES_FILE = (
    TRAINING_DATA_DIR
    / "training_examples.jsonl"
)


VALID_TRAINING_STAGES = {
    "storyline",
    "slide_content"
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


def _is_training_candidate(
    trace: dict
) -> bool:

    if trace.get("data_source") == "test":
        return False

    if trace.get("stage") not in VALID_TRAINING_STAGES:
        return False

    quality_signal = trace.get(
        "quality_signal",
        {}
    )

    if quality_signal.get(
        "decision"
    ) != "REVISE":
        return False

    if not quality_signal.get(
        "has_revision"
    ):
        return False

    if trace.get(
        "output_artifact"
    ) is None:
        return False

    return True


def _build_training_example(
    trace: dict
) -> dict:

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
        "input": {
            "topic_analysis": trace.get(
                "topic_analysis"
            ),
            "artifact": trace.get(
                "input_artifact"
            ),
            "critique": trace.get(
                "critique"
            )
        },
        "target": trace.get(
            "output_artifact"
        ),
        "metadata": {
            "source": trace.get(
                "data_source"
            ),
            "critic_score": trace.get(
                "quality_signal",
                {}
            ).get(
                "score"
            )
        }
    }


def build_training_dataset() -> list[dict]:

    print(
        "[DATASET BUILDER] "
        "Loading quality traces..."
    )

    traces = _load_quality_traces()

    training_examples = []

    for trace in traces:

        if not _is_training_candidate(
            trace
        ):
            continue

        example = _build_training_example(
            trace
        )

        training_examples.append(
            example
        )

    TRAINING_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with TRAINING_EXAMPLES_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        for example in training_examples:

            file.write(
                json.dumps(
                    example,
                    ensure_ascii=False
                )
            )

            file.write(
                "\n"
            )

    print(
        "[DATASET BUILDER] "
        f"Created {len(training_examples)} "
        "training examples."
    )

    return training_examples