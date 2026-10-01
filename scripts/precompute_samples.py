"""Run sample tenders through the DEPLOYED pipeline with fixed analysis ids, so judges get instant reports.

    python scripts/precompute_samples.py              # all samples
    python scripts/precompute_samples.py gem-7801296  # just one

Does what the API does for a user request: writes the analysis item and starts the state machine.
"""

import json
import sys
import time
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
REGION = "us-east-1"


def stack_outputs() -> dict:
    stack = boto3.client("cloudformation", region_name=REGION).describe_stacks(StackName="TenderLens")["Stacks"][0]
    return {o["OutputKey"]: o["OutputValue"] for o in stack["Outputs"]}


def main() -> None:
    out = stack_outputs()
    ddb = boto3.resource("dynamodb", region_name=REGION).Table(out["AnalysesTable"])
    sfn = boto3.client("stepfunctions", region_name=REGION)
    samples = json.loads((ROOT / "data" / "samples" / "samples.json").read_text(encoding="utf-8"))
    only = set(sys.argv[1:])
    for s in samples:
        if only and s["id"] not in only:
            continue
        now = int(time.time())
        key = f"samples/{s['pdf']}"
        ddb.put_item(Item={"id": s["analysis_id"], "status": "RUNNING", "step": "queued", "steps_done": [],
                           "tender_key": key, "profile_id": s["profile_id"], "created_at": now, "updated_at": now})
        sfn.start_execution(stateMachineArn=out["StateMachineArn"], name=f"{s['analysis_id']}-{now}",
                            input=json.dumps({"analysis_id": s["analysis_id"], "tender_key": key,
                                              "profile_id": s["profile_id"], "started_at": now}))
        print("started", s["analysis_id"])


if __name__ == "__main__":
    main()
