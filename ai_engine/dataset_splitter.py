import json
import os
import random
from pathlib import Path


TRAINING_DATA_DIR = Path(
    os.environ.get(
        "TRAINING_DATA_DIR",
        "training_data"
    )
)

CLEAN_DATASET_FILE = (
    TRAINING_DATA_DIR
    / "clean_training_examples.jsonl"
)

TRAIN_SPLIT_FILE = (
    TRAINING_DATA_DIR
    / "train.jsonl"
)

VALIDATION_SPLIT_FILE = (
    TRAINING_DATA_DIR
    / "validation.jsonl"
)


def _load_clean_dataset() -> list[dict]:

    if not CLEAN_DATASET_FILE.exists():
        raise FileNotFoundError(
            "Clean training dataset does not exist."
        )

    examples = []

    with CLEAN_DATASET_FILE.open(
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
                    "Invalid JSON in clean dataset "
                    f"at line {line_number}."
                ) from error

            examples.append(
                example
            )

    return examples


def _write_jsonl(
    file_path: Path,
    examples: list[dict]
) -> None:

    with file_path.open(
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


def split_training_dataset(
    validation_ratio: float = 0.2,
    random_seed: int = 42
) -> dict:

    if (
        isinstance(validation_ratio, bool)
        or not isinstance(
            validation_ratio,
            (int, float)
        )
    ):
        raise TypeError(
            "validation_ratio must be numeric."
        )

    if not 0 < validation_ratio < 1:
        raise ValueError(
            "validation_ratio must be between 0 and 1."
        )

    if (
        isinstance(random_seed, bool)
        or not isinstance(
            random_seed,
            int
        )
    ):
        raise TypeError(
            "random_seed must be an integer."
        )

    print(
        "[DATASET SPLITTER] "
        "Loading clean training dataset..."
    )

    examples = _load_clean_dataset()

    if len(examples) < 2:
        raise RuntimeError(
            "At least 2 clean training examples "
            "are required to create train and "
            "validation splits."
        )

    shuffled_examples = examples.copy()

    random.Random(
        random_seed
    ).shuffle(
        shuffled_examples
    )

    validation_count = max(
        1,
        round(
            len(shuffled_examples)
            * validation_ratio
        )
    )

    if validation_count >= len(
        shuffled_examples
    ):
        validation_count = (
            len(shuffled_examples) - 1
        )

    validation_examples = (
        shuffled_examples[
            :validation_count
        ]
    )

    train_examples = (
        shuffled_examples[
            validation_count:
        ]
    )

    TRAINING_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    _write_jsonl(
        TRAIN_SPLIT_FILE,
        train_examples
    )

    _write_jsonl(
        VALIDATION_SPLIT_FILE,
        validation_examples
    )

    statistics = {
        "total_examples": len(
            shuffled_examples
        ),
        "train_examples": len(
            train_examples
        ),
        "validation_examples": len(
            validation_examples
        ),
        "validation_ratio": validation_ratio,
        "random_seed": random_seed
    }

    print(
        "[DATASET SPLITTER] "
        f"Total examples: "
        f"{statistics['total_examples']}"
    )

    print(
        "[DATASET SPLITTER] "
        f"Train examples: "
        f"{statistics['train_examples']}"
    )

    print(
        "[DATASET SPLITTER] "
        f"Validation examples: "
        f"{statistics['validation_examples']}"
    )

    return statistics