from __future__ import annotations

import base64
import time

from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
    return _client


def image_to_data_url(image_bytes: bytes, mime_type: str = "image/png") -> str:
    return f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode()}"


def chat_json(
    messages: list[dict],
    model: str | None = None,
) -> tuple[dict, dict]:
    client = get_client()
    target_model = model or settings.llm_model
    last_error: Exception | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=settings.llm_temperature,
                response_format={"type": "json_object"},
                timeout=settings.llm_timeout_seconds,
            )
            content = response.choices[0].message.content or "{}"
            usage = response.usage
            usage_dict = {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
                "total_tokens": getattr(usage, "total_tokens", 0) or 0,
            }
            import json

            return json.loads(content), usage_dict
        except Exception as exc:
            last_error = exc
            if attempt < settings.llm_max_retries:
                time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"LLM call failed after retries: {last_error}") from last_error
