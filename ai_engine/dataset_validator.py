import json
import os
from pathlib import Path


TRAINING_DATA_DIR = Path(
    os.environ.get(
        "TRAINING_DATA_DIR",
        "training_data"
    )
)

TRAINING_EXAMPLES_FILE = (
    TRAINING_DATA_DIR
    / "training_examples.jsonl"
)

CLEAN_DATASET_FILE = (
    TRAINING_DATA_DIR
    / "clean_training_examples.jsonl"
)


VALID_STAGES = {
    "storyline",
    "slide_content"
}


def _load_training_examples() -> list[dict]:

    if not TRAINING_EXAMPLES_FILE.exists():
        raise FileNotFoundError(
            "Training examples file does not exist."
        )

    examples = []

    with TRAINING_EXAMPLES_FILE.open(
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
                example = json.loads(
                    line
                )

            except json.JSONDecodeError as error:
                raise RuntimeError(
                    "Invalid JSON in training examples "
                    f"at line {line_number}."
                ) from error

            examples.append(
                example
            )

    return examples


def _validate_example(
    example: dict
) -> bool:

    if not isinstance(
        example,
        dict
    ):
        return False

    required_fields = {
        "example_id",
        "stage",
        "topic",
        "input",
        "target",
        "metadata"
    }

    if not required_fields.issubset(
        example.keys()
    ):
        return False

    example_id = example.get(
        "example_id"
    )

    if (
        not isinstance(example_id, str)
        or not example_id.strip()
    ):
        return False

    if example.get(
        "stage"
    ) not in VALID_STAGES:
        return False

    topic = example.get(
        "topic"
    )

    if (
        not isinstance(topic, str)
        or not topic.strip()
    ):
        return False

    input_data = example.get(
        "input"
    )

    target = example.get(
        "target"
    )

    metadata = example.get(
        "metadata"
    )

    if not isinstance(
        input_data,
        dict
    ):
        return False

    if not isinstance(
        target,
        dict
    ):
        return False

    if not isinstance(
        metadata,
        dict
    ):
        return False

    required_input_fields = {
        "topic_analysis",
        "artifact",
        "critique"
    }

    if not required_input_fields.issubset(
        input_data.keys()
    ):
        return False

    if not isinstance(
        input_data.get("topic_analysis"),
        dict
    ):
        return False

    if not isinstance(
        input_data.get("artifact"),
        dict
    ):
        return False

    if not isinstance(
        input_data.get("critique"),
        dict
    ):
        return False

    if not target:
        return False

    if input_data.get(
        "artifact"
    ) == target:
        return False

    critic_score = metadata.get(
        "critic_score"
    )

    if (
        isinstance(critic_score, bool)
        or not isinstance(
            critic_score,
            (int, float)
        )
    ):
        return False

    if not 0 <= critic_score <= 10:
        return False

    return True


def _example_fingerprint(
    example: dict
) -> str:

    fingerprint_data = {
        "stage": example.get(
            "stage"
        ),
        "topic": example.get(
            "topic"
        ),
        "input": example.get(
            "input"
        ),
        "target": example.get(
            "target"
        )
    }

    return json.dumps(
        fingerprint_data,
        sort_keys=True,
        ensure_ascii=False
    )


def validate_training_dataset() -> list[dict]:

    print(
        "[DATASET VALIDATOR] "
        "Validating training examples..."
    )

    examples = _load_training_examples()

    clean_examples = []

    seen_fingerprints = set()

    invalid_count = 0
    duplicate_count = 0

    for example in examples:

        if not _validate_example(
            example
        ):
            invalid_count += 1
            continue

        fingerprint = _example_fingerprint(
            example
        )

        if fingerprint in seen_fingerprints:
            duplicate_count += 1
            continue

        seen_fingerprints.add(
            fingerprint
        )

        clean_examples.append(
            example
        )

    TRAINING_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with CLEAN_DATASET_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        for example in clean_examples:

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
        "[DATASET VALIDATOR] "
        f"Valid examples: {len(clean_examples)}"
    )

    print(
        "[DATASET VALIDATOR] "
        f"Invalid examples removed: {invalid_count}"
    )

    print(
        "[DATASET VALIDATOR] "
        f"Duplicates removed: {duplicate_count}"
    )

    return clean_examples