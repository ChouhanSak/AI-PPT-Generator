import json
import os
from collections import Counter
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


def _load_clean_examples() -> list[dict]:

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


def calculate_dataset_statistics() -> dict:

    print(
        "[DATASET STATISTICS] "
        "Analyzing clean dataset..."
    )

    examples = _load_clean_examples()

    stage_counts = Counter()
    source_counts = Counter()
    topic_counts = Counter()

    critic_scores = []

    for example in examples:

        stage_counts[
            example.get("stage")
        ] += 1

        metadata = example.get(
            "metadata",
            {}
        )

        source_counts[
            metadata.get("source")
        ] += 1

        topic_counts[
            example.get("topic")
        ] += 1

        score = metadata.get(
            "critic_score"
        )

        if (
            not isinstance(score, bool)
            and isinstance(
                score,
                (int, float)
            )
        ):
            critic_scores.append(
                score
            )

    average_score = None

    if critic_scores:
        average_score = (
            sum(critic_scores)
            / len(critic_scores)
        )

    statistics = {
        "total_examples": len(examples),
        "stage_distribution": dict(
            stage_counts
        ),
        "source_distribution": dict(
            source_counts
        ),
        "unique_topics": len(
            topic_counts
        ),
        "topic_distribution": dict(
            topic_counts
        ),
        "critic_score": {
            "count": len(
                critic_scores
            ),
            "minimum": (
                min(critic_scores)
                if critic_scores
                else None
            ),
            "maximum": (
                max(critic_scores)
                if critic_scores
                else None
            ),
            "average": average_score
        }
    }

    print(
        "[DATASET STATISTICS] "
        f"Total examples: "
        f"{statistics['total_examples']}"
    )

    print(
        "[DATASET STATISTICS] "
        f"Unique topics: "
        f"{statistics['unique_topics']}"
    )

    print(
        "[DATASET STATISTICS] "
        f"Stage distribution: "
        f"{statistics['stage_distribution']}"
    )

    print(
        "[DATASET STATISTICS] "
        f"Source distribution: "
        f"{statistics['source_distribution']}"
    )

    print(
        "[DATASET STATISTICS] "
        f"Average critic score: "
        f"{statistics['critic_score']['average']}"
    )

    return statistics