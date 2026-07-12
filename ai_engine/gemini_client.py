import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


PRIMARY_MODEL = "gemini-3.5-flash"

FALLBACK_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]

MODEL_CHAIN = [
    PRIMARY_MODEL,
    *FALLBACK_MODELS,
]


class GeminiError(RuntimeError):
    pass


class GeminiQuotaExceededError(GeminiError):
    pass


class GeminiTemporaryError(GeminiError):
    pass


def _is_daily_quota_error(
    error_text: str
) -> bool:

    text = error_text.lower()

    daily_quota_markers = [
        "generaterequestsperdayperprojectpermodel",
        "requestsperdayperprojectpermodel",
        "perdayperprojectpermodel",
        "generate requests per day",
    ]

    return (
        "429" in text
        and any(
            marker in text
            for marker in daily_quota_markers
        )
    )


def _is_rate_limit_error(
    error_text: str
) -> bool:

    text = error_text.lower()

    rate_limit_markers = [
        "generaterequestsperminuteperprojectpermodel",
        "requestsperminuteperprojectpermodel",
        "perminuteperprojectpermodel",
        "generate requests per minute",
        "retrydelay",
        "please retry in",
    ]

    return (
        "429" in text
        and any(
            marker in text
            for marker in rate_limit_markers
        )
    )


def _is_temporary_error(
    error_text: str
) -> bool:

    text = error_text.lower()

    temporary_markers = [
        "503",
        "unavailable",
        "high demand",
        "temporarily unavailable",
        "service unavailable",
        "resource exhausted",
        "429",
    ]

    return any(
        marker in text
        for marker in temporary_markers
    )


def _is_model_unavailable_error(
    error_text: str
) -> bool:

    text = error_text.lower()

    model_error_markers = [
        "404",
        "model not found",
        "is not found",
        "not supported",
    ]

    return any(
        marker in text
        for marker in model_error_markers
    )


def _extract_retry_seconds(
    error_text: str
) -> int | None:

    patterns = [
        r"retry in ([0-9.]+)s",
        r"retrydelay['\"]?\s*:\s*['\"]?([0-9.]+)s",
        r"retrydelay['\"]?\s*:\s*['\"]?([0-9.]+)s['\"]?",
    ]

    text = error_text.lower()

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            return max(
                1,
                int(
                    float(
                        match.group(1)
                    )
                ) + 1
            )

    return None


def _generate_with_model(
    *,
    client,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int,
    caller_name: str,
    max_retries: int
) -> str:

    last_error = None

    for attempt in range(
        1,
        max_retries + 1
    ):

        try:

            print(
                f"[{caller_name}] "
                f"Model: {model}"
            )

            print(
                f"[{caller_name}] "
                f"API attempt "
                f"{attempt}/{max_retries}"
            )

            response = (
                client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type=(
                            "application/json"
                        ),
                        temperature=temperature,
                        max_output_tokens=(
                            max_output_tokens
                        )
                    )
                )
            )

            if not response.text:

                raise GeminiError(
                    f"{caller_name} returned "
                    "an empty response."
                )

            print(
                f"[{caller_name}] "
                f"Model succeeded: {model}"
            )

            return response.text

        except GeminiError:
            raise

        except Exception as api_error:

            last_error = api_error

            error_text = str(
                api_error
            )

            if _is_daily_quota_error(
                error_text
            ):

                raise GeminiQuotaExceededError(
                    "Gemini daily free-tier quota "
                    f"is exhausted for model {model}."
                ) from api_error

            if _is_rate_limit_error(
                error_text
            ):

                retry_seconds = (
                    _extract_retry_seconds(
                        error_text
                    )
                )

                wait_seconds = (
                    retry_seconds
                    if retry_seconds is not None
                    else 20
                )

                if attempt < max_retries:

                    print(
                        f"[{caller_name}] "
                        f"Per-minute rate limit "
                        f"hit on {model}. "
                        f"Waiting {wait_seconds} "
                        "seconds..."
                    )

                    time.sleep(
                        wait_seconds
                    )

                    continue

                print(
                    f"[{caller_name}] "
                    f"Rate limit still active "
                    f"on {model}. "
                    "Trying fallback model..."
                )

                break

            if _is_model_unavailable_error(
                error_text
            ):

                print(
                    f"[{caller_name}] "
                    f"Model unavailable: {model}"
                )

                break

            if not _is_temporary_error(
                error_text
            ):

                raise GeminiError(
                    "Gemini API request failed: "
                    f"{api_error}"
                ) from api_error

            if attempt == max_retries:

                break

            retry_seconds = (
                _extract_retry_seconds(
                    error_text
                )
            )

            wait_seconds = (
                retry_seconds
                if retry_seconds is not None
                else min(
                    3 * attempt,
                    10
                )
            )

            print(
                f"[{caller_name}] "
                f"Temporary error on {model}. "
                f"Retrying in "
                f"{wait_seconds} seconds..."
            )

            time.sleep(
                wait_seconds
            )

    raise GeminiTemporaryError(
        f"{model} remained unavailable "
        f"after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


def generate_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 3000,
    caller_name: str = "GEMINI",
    max_retries: int = 2
) -> str:

    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:

        raise GeminiError(
            "GEMINI_API_KEY is missing "
            "from .env file."
        )

    client = genai.Client(
        api_key=api_key
    )

    model_errors = []
    quota_errors = []

    for model in MODEL_CHAIN:

        try:

            return _generate_with_model(
                client=client,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                caller_name=caller_name,
                max_retries=max_retries
            )

        except GeminiQuotaExceededError as error:

            quota_errors.append(
                str(error)
            )

            print(
                f"[{caller_name}] "
                f"Daily quota unavailable "
                f"for {model}. "
                "Trying next model..."
            )

            continue

        except GeminiTemporaryError as error:

            model_errors.append(
                str(error)
            )

            print(
                f"[{caller_name}] "
                f"Switching from {model} "
                "to fallback model..."
            )

            continue

    if (
        quota_errors
        and len(quota_errors) == len(MODEL_CHAIN)
    ):

        raise GeminiQuotaExceededError(
            "Daily Gemini quota is exhausted "
            "for all configured models."
        )

    all_errors = (
        model_errors
        + quota_errors
    )

    raise GeminiTemporaryError(
        "All configured Gemini models "
        "were unavailable. "
        + " | ".join(
            all_errors
        )
    )