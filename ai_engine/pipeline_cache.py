import hashlib
import json
from pathlib import Path


CACHE_DIR = Path(
    "pipeline_cache"
)


def _build_cache_key(
    title: str,
    total_slides: int,
    audience: str,
    tone: str
) -> str:

    payload = {
        "title": title.strip().lower(),
        "total_slides": total_slides,
        "audience": audience.strip().lower(),
        "tone": tone.strip().lower()
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.sha256(
        serialized.encode(
            "utf-8"
        )
    ).hexdigest()


def _get_cache_file(
    *,
    title: str,
    total_slides: int,
    audience: str,
    tone: str,
    stage: str
) -> Path:

    cache_key = _build_cache_key(
        title=title,
        total_slides=total_slides,
        audience=audience,
        tone=tone
    )

    return (
        CACHE_DIR
        / cache_key
        / f"{stage}.json"
    )


def save_pipeline_cache(
    *,
    title: str,
    total_slides: int,
    audience: str,
    tone: str,
    stage: str,
    data: dict
) -> None:

    cache_file = _get_cache_file(
        title=title,
        total_slides=total_slides,
        audience=audience,
        tone=tone,
        stage=stage
    )

    cache_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with cache_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "[PIPELINE CACHE] "
        f"Saved stage: {stage}"
    )


def load_pipeline_cache(
    *,
    title: str,
    total_slides: int,
    audience: str,
    tone: str,
    stage: str
) -> dict | None:

    cache_file = _get_cache_file(
        title=title,
        total_slides=total_slides,
        audience=audience,
        tone=tone,
        stage=stage
    )

    if not cache_file.exists():

        print(
            "[PIPELINE CACHE] "
            f"Cache miss: {stage}"
        )

        return None

    try:

        with cache_file.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

    except (
        json.JSONDecodeError,
        OSError
    ):

        print(
            "[PIPELINE CACHE] "
            f"Invalid cache ignored: {stage}"
        )

        return None

    print(
        "[PIPELINE CACHE] "
        f"Cache hit: {stage}"
    )

    return data


def clear_pipeline_cache() -> None:

    if not CACHE_DIR.exists():
        return

    for cache_file in CACHE_DIR.rglob(
        "*.json"
    ):

        cache_file.unlink()

    directories = sorted(
        [
            path
            for path in CACHE_DIR.rglob("*")
            if path.is_dir()
        ],
        key=lambda path: len(
            path.parts
        ),
        reverse=True
    )

    for directory in directories:

        try:
            directory.rmdir()

        except OSError:
            pass

    print(
        "[PIPELINE CACHE] "
        "Cache cleared."
    )