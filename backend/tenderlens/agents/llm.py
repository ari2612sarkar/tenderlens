"""Claude on Amazon Bedrock (Messages API via the Mantle endpoint) with structured outputs."""

import logging
import os
import time
from functools import lru_cache
from typing import TypeVar

from anthropic import AnthropicBedrockMantle, BetaRefusalFallbackMiddleware
from pydantic import BaseModel

log = logging.getLogger(__name__)

MODEL = os.environ.get("TL_MODEL", "anthropic.claude-opus-5-5")
FALLBACK_MODEL = os.environ.get("TL_FALLBACK_MODEL", "anthropic.claude-opus-4-8")
REGION = os.environ.get("TL_BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _client() -> AnthropicBedrockMantle:
    # Refusal fallback is client-side on Bedrock; a refused request is retried once on FALLBACK_MODEL.
    return AnthropicBedrockMantle(
        aws_region=REGION,
        max_retries=4,
        timeout=600.0,
        middleware=[BetaRefusalFallbackMiddleware([{"model": FALLBACK_MODEL}])],
    )


def structured(system: str, user: str, output_format: type[T], *, effort: str = "medium",
               max_tokens: int = 24_000) -> tuple[T, dict]:
    """One structured-output call. Returns (parsed object, usage/metadata)."""
    started = time.monotonic()
    response = _client().beta.messages.parse(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=output_format,
        output_config={"effort": effort},
    )
    meta = {
        "model": response.model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "seconds": round(time.monotonic() - started, 1),
        "request_id": getattr(response, "_request_id", None),
    }
    log.info("llm call %s", meta)
    if response.stop_reason == "refusal":
        raise LLMError(f"Model declined the request ({getattr(response.stop_details, 'category', None)}).")
    if response.stop_reason == "max_tokens":
        raise LLMError("Model output was cut off (max_tokens).")
    if response.parsed_output is None:
        raise LLMError("Model returned no structured output.")
    return response.parsed_output, meta
