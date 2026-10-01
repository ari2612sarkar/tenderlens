"""Claude on Amazon Bedrock (Messages API via the Mantle endpoint).

Structured outputs aren't available on the Bedrock Mantle endpoint, and current models reject
forced tool_choice, so each call offers a single `submit` tool whose input schema is the Pydantic
model, asks the model to call it, and validates the input. One repair round on validation errors.
"""

import logging
import os
import time
from functools import lru_cache
from typing import TypeVar

from anthropic import AnthropicBedrockMantle, BetaRefusalFallbackMiddleware
from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

MODEL = os.environ.get("TL_MODEL", "anthropic.claude-opus-5-5")
FALLBACK_MODEL = os.environ.get("TL_FALLBACK_MODEL", "anthropic.claude-opus-4-8")
REGION = os.environ.get("TL_BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
USE_FALLBACK = os.environ.get("TL_REFUSAL_FALLBACK", "1") == "1"

SUBMIT_INSTRUCTION = ("\n\nWhen you have finished, call the `submit` tool exactly once with the complete result. "
                      "Do not answer in plain text.")

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _client() -> AnthropicBedrockMantle:
    # Bedrock has no server-side `fallbacks`; the SDK middleware retries a refused request on FALLBACK_MODEL.
    middleware = [BetaRefusalFallbackMiddleware([{"model": FALLBACK_MODEL}])] if USE_FALLBACK else None
    return AnthropicBedrockMantle(aws_region=REGION, max_retries=4, timeout=840.0, middleware=middleware)


def structured(system: str, user: str, output_format: type[T], *, effort: str = "medium",
               max_tokens: int = 32_000) -> tuple[T, dict]:
    """Ask for a result shaped like `output_format`. Returns (validated object, call metadata)."""
    tool = {
        "name": "submit",
        "description": "Submit the final result.",
        "input_schema": output_format.model_json_schema(),
    }
    messages: list = [{"role": "user", "content": user}]
    meta = {"model": MODEL, "input_tokens": 0, "output_tokens": 0, "calls": 0}
    started = time.monotonic()

    for _ in range(2):
        with _client().beta.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            system=system + SUBMIT_INSTRUCTION,
            messages=messages,
            tools=[tool],
            tool_choice={"type": "auto"},
            output_config={"effort": effort},
        ) as stream:
            response = stream.get_final_message()

        meta["calls"] += 1
        meta["model"] = response.model
        meta["input_tokens"] += response.usage.input_tokens
        meta["output_tokens"] += response.usage.output_tokens
        meta["request_id"] = getattr(response, "_request_id", None)

        if response.stop_reason == "refusal":
            raise LLMError(f"Model declined the request ({getattr(response.stop_details, 'category', None)}).")
        if response.stop_reason == "max_tokens":
            raise LLMError("Model output was cut off (max_tokens).")

        call = next((b for b in response.content if b.type == "tool_use" and b.name == "submit"), None)
        messages.append({"role": "assistant", "content": response.content})
        if call is None:
            messages.append({"role": "user", "content": "Please call the `submit` tool with the complete result."})
            continue
        try:
            result = output_format.model_validate(call.input)
        except ValidationError as err:
            log.warning("submit input failed validation: %s", err)
            messages.append({"role": "user", "content": [{
                "type": "tool_result", "tool_use_id": call.id, "is_error": True,
                "content": f"The result failed validation:\n{err}\nCall `submit` again with a corrected result.",
            }]})
            continue
        meta["seconds"] = round(time.monotonic() - started, 1)
        log.info("llm ok %s", meta)
        return result, meta

    raise LLMError("Model did not return a valid result after a repair attempt.")
