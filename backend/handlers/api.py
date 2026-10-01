"""HTTP API (API Gateway v2 payload) for the TenderLens web app."""

import base64
import json
import logging
import os
import re
import time
import uuid
from datetime import date
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError
from pydantic import ValidationError

from handlers.common import (
    ANALYSES_TABLE, BUCKET, DATA_DIR, PROFILES_TABLE, artifact, demo_profiles, from_ddb, get_json,
    load_profile, s3, table, to_ddb,
)
from tenderlens.evaluate import evaluate_scheme
from tenderlens.models import CompanyProfile, Criterion
from tenderlens.taxonomy import WORK_TAGS

logging.getLogger().setLevel(logging.INFO)

STATE_MACHINE_ARN = os.environ.get("TL_STATE_MACHINE_ARN", "")
DAILY_LIMIT = int(os.environ.get("TL_DAILY_ANALYSES_PER_IP", "10"))
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
DAY = 86_400


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _response(status: int, body) -> dict:
    return {"statusCode": status, "headers": {"content-type": "application/json", "cache-control": "no-store"},
            "body": json.dumps(body, ensure_ascii=False, default=str)}


def _body(event) -> dict:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    try:
        return json.loads(raw)
    except ValueError as err:
        raise HttpError(400, "Body must be JSON.") from err


def _client_ip(event) -> str:
    forwarded = (event.get("headers") or {}).get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or event["requestContext"]["http"].get("sourceIp", "unknown")


@lru_cache(maxsize=1)
def _samples() -> list[dict]:
    return json.loads((DATA_DIR / "samples" / "samples.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _schemes() -> list[dict]:
    path = DATA_DIR / "schemes" / "schemes.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


# --- routes ------------------------------------------------------------------------

def get_samples(_event, _params):
    return {"samples": _samples(), "profiles": list(demo_profiles().values())}


def get_taxonomy(_event, _params):
    return {"work_tags": WORK_TAGS}


def _validated_profile(body: dict) -> dict:
    try:
        return CompanyProfile.model_validate(body).model_dump()
    except ValidationError as err:
        raise HttpError(400, f"Invalid profile: {err.errors()[0]['loc']} {err.errors()[0]['msg']}") from err


def create_profile(event, _params):
    profile = _validated_profile(_body(event))
    profile["id"] = "p-" + uuid.uuid4().hex[:12]
    table(PROFILES_TABLE).put_item(Item=to_ddb({"id": profile["id"], "profile": profile,
                                                "expires_at": int(time.time()) + 180 * DAY}))
    return profile


def update_profile(event, params):
    pid = params["id"]
    if pid in demo_profiles():
        raise HttpError(403, "Demo profiles are read-only. Save a copy instead.")
    if load_profile(pid) is None:
        raise HttpError(404, "Profile not found.")
    profile = _validated_profile(_body(event))
    profile["id"] = pid
    table(PROFILES_TABLE).put_item(Item=to_ddb({"id": pid, "profile": profile,
                                                "expires_at": int(time.time()) + 180 * DAY}))
    return profile


def get_profile(_event, params):
    profile = load_profile(params["id"])
    if profile is None:
        raise HttpError(404, "Profile not found.")
    return profile


def create_upload(event, _params):
    body = _body(event)
    if int(body.get("size", 0)) > MAX_UPLOAD_BYTES:
        raise HttpError(413, "PDF is larger than 25 MB.")
    key = f"uploads/{uuid.uuid4().hex}.pdf"
    url = s3().generate_presigned_url(
        "put_object", Params={"Bucket": BUCKET, "Key": key, "ContentType": "application/pdf"}, ExpiresIn=900)
    return {"upload_url": url, "tender_key": key}


def _take_rate_slot(ip: str) -> None:
    key = f"rate#{ip}#{date.today().isoformat()}"
    try:
        table(ANALYSES_TABLE).update_item(
            Key={"id": key},
            UpdateExpression="ADD hits :one SET expires_at = :exp",
            ConditionExpression="attribute_not_exists(hits) OR hits < :limit",
            ExpressionAttributeValues={":one": 1, ":limit": DAILY_LIMIT, ":exp": int(time.time()) + 2 * DAY},
        )
    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HttpError(429, f"Daily limit of {DAILY_LIMIT} live analyses reached. Try a sample report.") from err
        raise


def create_analysis(event, _params):
    body = _body(event)
    profile_id = body.get("profile_id", "")
    if load_profile(profile_id) is None:
        raise HttpError(400, "Unknown profile_id.")
    if body.get("sample_id"):
        sample = next((s for s in _samples() if s["id"] == body["sample_id"]), None)
        if sample is None:
            raise HttpError(400, "Unknown sample_id.")
        tender_key = f"samples/{sample['pdf']}"
    else:
        tender_key = body.get("tender_key", "")
        if not re.fullmatch(r"uploads/[0-9a-f]{32}\.pdf", tender_key):
            raise HttpError(400, "Invalid tender_key.")
    _take_rate_slot(_client_ip(event))
    return start_analysis(tender_key, profile_id)


def start_analysis(tender_key: str, profile_id: str, analysis_id: str | None = None) -> dict:
    aid = analysis_id or "a-" + uuid.uuid4().hex[:16]
    now = int(time.time())
    table(ANALYSES_TABLE).put_item(Item={
        "id": aid, "status": "RUNNING", "step": "queued", "steps_done": [], "tender_key": tender_key,
        "profile_id": profile_id, "created_at": now, "updated_at": now,
    })
    boto3.client("stepfunctions").start_execution(
        stateMachineArn=STATE_MACHINE_ARN, name=f"{aid}-{now}",
        input=json.dumps({"analysis_id": aid, "tender_key": tender_key, "profile_id": profile_id,
                          "started_at": now}),
    )
    return {"id": aid, "status": "RUNNING"}


def get_analysis(_event, params):
    aid = params["id"]
    item = table(ANALYSES_TABLE).get_item(Key={"id": aid}).get("Item")
    if not item or aid.startswith("rate#"):
        raise HttpError(404, "Analysis not found.")
    item = from_ddb(item)
    out = {k: item.get(k) for k in ("id", "status", "step", "steps_done", "error", "verdict", "title",
                                    "organisation", "profile_id", "created_at", "updated_at")}
    if item["status"] == "DONE":
        out["report"] = get_json(artifact(aid, "report"))
        out["pdf_url"] = s3().generate_presigned_url(
            "get_object", ExpiresIn=3600,
            Params={"Bucket": BUCKET, "Key": item["tender_key"], "ResponseContentType": "application/pdf",
                    "ResponseContentDisposition": "inline"})
    return out


def match_schemes(event, _params):
    pid = (event.get("queryStringParameters") or {}).get("profile_id", "")
    profile = load_profile(pid)
    if profile is None:
        raise HttpError(404, "Profile not found.")
    company = CompanyProfile.model_validate(profile)
    order = {"ELIGIBLE": 0, "POSSIBLY_ELIGIBLE": 1, "NOT_ELIGIBLE": 2}
    matches = []
    for scheme in _schemes():
        ev = evaluate_scheme(criteria=[Criterion.model_validate(c) for c in scheme["criteria"]],
                             profile=company, as_of=date.today())
        matches.append({**{k: scheme.get(k) for k in ("id", "name", "benefit", "ministry", "source_url")},
                        "verdict": ev.verdict, "results": ev.model_dump()["results"]})
    matches.sort(key=lambda m: order[m["verdict"]])
    return {"profile_id": pid, "matches": matches}


ROUTES = [
    ("GET", r"/api/health", lambda e, p: {"ok": True}),
    ("GET", r"/api/samples", get_samples),
    ("GET", r"/api/taxonomy", get_taxonomy),
    ("POST", r"/api/profiles", create_profile),
    ("GET", r"/api/profiles/(?P<id>[\w-]+)", get_profile),
    ("PUT", r"/api/profiles/(?P<id>[\w-]+)", update_profile),
    ("POST", r"/api/uploads", create_upload),
    ("POST", r"/api/analyses", create_analysis),
    ("GET", r"/api/analyses/(?P<id>[\w-]+)", get_analysis),
    ("GET", r"/api/schemes/match", match_schemes),
]


def handler(event, _context):
    method = event["requestContext"]["http"]["method"]
    path = event.get("rawPath", "")
    try:
        for route_method, pattern, fn in ROUTES:
            match = re.fullmatch(pattern, path)
            if match and method == route_method:
                return _response(200, fn(event, match.groupdict()))
        raise HttpError(404, "Not found.")
    except HttpError as err:
        return _response(err.status, {"error": str(err)})
    except Exception:  # noqa: BLE001
        logging.exception("unhandled error")
        return _response(500, {"error": "Something went wrong."})
