"""Shared AWS helpers for the Lambda handlers."""

import json
import os
import time
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import boto3

BUCKET = os.environ.get("TL_BUCKET", "")
ANALYSES_TABLE = os.environ.get("TL_ANALYSES_TABLE", "")
PROFILES_TABLE = os.environ.get("TL_PROFILES_TABLE", "")
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=None)
def s3():
    return boto3.client("s3")


@lru_cache(maxsize=None)
def table(name: str):
    return boto3.resource("dynamodb").Table(name)


def put_json(key: str, value) -> None:
    s3().put_object(Bucket=BUCKET, Key=key, Body=json.dumps(value, ensure_ascii=False).encode(),
                    ContentType="application/json")


def get_json(key: str):
    return json.loads(s3().get_object(Bucket=BUCKET, Key=key)["Body"].read())


def artifact(analysis_id: str, name: str) -> str:
    return f"analyses/{analysis_id}/{name}.json"


def from_ddb(value):
    """DynamoDB returns Decimals; convert back to int/float."""
    if isinstance(value, list):
        return [from_ddb(v) for v in value]
    if isinstance(value, dict):
        return {k: from_ddb(v) for k, v in value.items()}
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def to_ddb(value):
    return json.loads(json.dumps(value), parse_float=Decimal)


def mark_step(analysis_id: str, step: str) -> None:
    table(ANALYSES_TABLE).update_item(
        Key={"id": analysis_id},
        UpdateExpression="SET step = :s, updated_at = :t, steps_done = list_append(if_not_exists(steps_done, :e), :l)",
        ExpressionAttributeValues={":s": step, ":t": int(time.time()), ":e": [], ":l": [step]},
    )


@lru_cache(maxsize=1)
def demo_profiles() -> dict[str, dict]:
    profiles = {}
    for path in (DATA_DIR / "profiles").glob("*.json"):
        p = json.loads(path.read_text(encoding="utf-8"))
        profiles[p["id"]] = p
    return profiles


def load_profile(profile_id: str) -> dict | None:
    if profile_id in demo_profiles():
        return demo_profiles()[profile_id]
    item = table(PROFILES_TABLE).get_item(Key={"id": profile_id}).get("Item")
    return from_ddb(item["profile"]) if item else None
