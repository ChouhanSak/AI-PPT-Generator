import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

MODEL = "gemini-3.5-flash"


class GeminiError(RuntimeError):
    pass


class GeminiQuotaExceededError(GeminiError):
    pass


class GeminiTemporaryError(GeminiError):
    pass


def _is_daily_quota_error(error_text: str) -> bool:
    text = error_text.lower()

    daily_quota_markers = [
        "generaterequestsperdayperprojectpermodel",
        "requestsperday",
        "perdayperproject",
        "free_tier_requests",
        "quota exceeded for metric",
    ]

    return (
        "429" in text
        and any(
            marker in text
            for marker in daily_quota_markers
        )
    )


def _is_temporary_error(error_text: str) -> bool:
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


def _extract_retry_seconds(
    error_text: str
) -> int | None:

    patterns = [
        r"retry in ([0-9.]+)s",
        r"retrydelay['\"]?\s*:\s*['\"]?([0-9.]+)s",
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
                )
            )

    return None


def generate_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 3000,
    caller_name: str = "GEMINI",
    max_retries: int = 4
) -> str:

    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise GeminiError(
            "GEMINI_API_KEY is missing from .env file."
        )

    client = genai.Client(
        api_key=api_key
    )

    for attempt in range(
        1,
        max_retries + 1
    ):
        try:
            print(
                f"[{caller_name}] API attempt "
                f"{attempt}/{max_retries}"
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=temperature,
                    max_output_tokens=max_output_tokens
                )
            )

            if not response.text:
                raise GeminiError(
                    f"{caller_name} returned an empty response."
                )

            return response.text

        except GeminiError:
            raise

        except Exception as api_error:
            error_text = str(
                api_error
            )

            if _is_daily_quota_error(
                error_text
            ):
                raise GeminiQuotaExceededError(
                    "Gemini daily free-tier quota is exhausted. "
                    "The request was stopped immediately because "
                    "retrying cannot restore a daily quota."
                ) from api_error

            if not _is_temporary_error(
                error_text
            ):
                raise GeminiError(
                    f"Gemini API request failed: {api_error}"
                ) from api_error

            if attempt == max_retries:
                raise GeminiTemporaryError(
                    "Gemini API remained unavailable after "
                    f"{max_retries} attempts. "
                    f"Last error: {api_error}"
                ) from api_error

            retry_seconds = _extract_retry_seconds(
                error_text
            )

            wait_seconds = (
                retry_seconds
                if retry_seconds is not None
                else 5 * attempt
            )

            print(
                f"[{caller_name}] "
                "Temporary Gemini error. "
                f"Retrying in {wait_seconds} seconds..."
            )

            time.sleep(
                wait_seconds
            )

    raise GeminiError(
        "Gemini request ended unexpectedly."
    )