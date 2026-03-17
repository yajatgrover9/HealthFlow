from __future__ import annotations

from dataclasses import dataclass

from src.app.core.config import settings


class GenAIError(RuntimeError):
    pass


@dataclass(frozen=True)
class GenAIResult:
    model: str
    text: str


def _gemini_generate(prompt: str) -> GenAIResult:
    """Generate content using Google's official `google-genai` SDK.

    Env vars:
    - GEMINI_API_KEY (preferred)
    - GENAI_API_KEY (fallback for our app settings)

    Notes:
    - This is deliberately synchronous for MVP simplicity.
    - For high throughput, move generation to a background worker.
    """

    api_key = settings.GEMINI_API_KEY or settings.GENAI_API_KEY
    if not api_key:
        raise GenAIError("GEMINI_API_KEY / GENAI_API_KEY not configured")

    try:
        from google import genai  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise GenAIError(
            "google-genai is not installed. Install it with: pip install -U google-genai"
        ) from e

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=settings.GENAI_MODEL, contents=prompt
        )
        text = getattr(response, "text", None)
        if not text:
            raise GenAIError("Empty response from Gemini")
        return GenAIResult(model=settings.GENAI_MODEL, text=text)
    except GenAIError:
        raise
    except Exception as e:  # noqa: BLE001
        raise GenAIError(f"Gemini request failed: {e}") from e


def generate_patient_summary(prompt: str) -> GenAIResult:
    provider = (settings.GENAI_PROVIDER or "gemini").lower().strip()
    if provider in {"gemini", "google"}:
        return _gemini_generate(prompt)

    raise GenAIError(f"Unsupported GENAI_PROVIDER: {provider}")
