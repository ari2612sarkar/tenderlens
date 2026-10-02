"""Find a Claude model this AWS account can call on Bedrock, then exercise TenderLens's real agent path.

    backend/.venv/Scripts/python scripts/smoke_bedrock.py          # report only
    backend/.venv/Scripts/python scripts/smoke_bedrock.py --pin    # also pin the working model in infra/cdk.json
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from anthropic import AnthropicBedrockMantle  # noqa: E402
from pydantic import BaseModel  # noqa: E402

CANDIDATES = ["anthropic.claude-opus-5-5", "anthropic.claude-opus-4-8", "anthropic.claude-sonnet-5-5",
              "anthropic.claude-sonnet-5"]
REGION = "us-east-1"


class Ping(BaseModel):
    city: str
    state: str


def try_model(client: AnthropicBedrockMantle, model: str) -> str | None:
    try:
        msg = client.messages.create(model=model, max_tokens=64,
                                     messages=[{"role": "user", "content": "Reply with the single word: ready"}])
        return next((b.text for b in msg.content if b.type == "text"), "").strip() or "(no text)"
    except Exception as err:  # noqa: BLE001 - we want the message whatever the class
        print(f"  {model}: FAILED {type(err).__name__}: {str(err)[:200]}")
        return None


def main() -> None:
    client = AnthropicBedrockMantle(aws_region=REGION, max_retries=1)
    working = []
    for model in CANDIDATES:
        reply = try_model(client, model)
        if reply is not None:
            print(f"  {model}: OK ({reply!r})")
            working.append(model)
    if not working:
        sys.exit("No Claude model is callable. Check Bedrock model access in us-east-1 and the account plan.")

    model = working[0]
    fallback = next((m for m in working[1:] if "opus" in m), working[-1] if len(working) > 1 else model)
    os.environ["TL_MODEL"], os.environ["TL_FALLBACK_MODEL"] = model, fallback

    # Exercise the exact production path: submit tool + effort + refusal-fallback middleware.
    from tenderlens.agents.llm import structured

    result, meta = structured("Extract the place mentioned.", "The bid office is in Kharagpur, West Bengal.", Ping,
                              effort="low", max_tokens=4000)
    print(f"agent path OK with {model}: {result.model_dump()} {meta}")

    if "--pin" in sys.argv:
        cdk = ROOT / "infra" / "cdk.json"
        conf = json.loads(cdk.read_text(encoding="utf-8"))
        conf["context"].update({"model": model, "fallback_model": fallback})
        cdk.write_text(json.dumps(conf, indent=2) + "\n", encoding="utf-8")
        print(f"pinned model={model} fallback={fallback} in {cdk}")


if __name__ == "__main__":
    main()
