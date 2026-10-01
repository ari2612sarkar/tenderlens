"""Step Functions task handlers. State carries only ids; artifacts live in S3."""

import io
import logging
import time
from datetime import date

import boto3
from pypdf import PdfReader, PdfWriter

from handlers.common import (
    ANALYSES_TABLE, BUCKET, artifact, get_json, load_profile, mark_step, put_json, s3, table, to_ddb,
)
from tenderlens.document import build_document, clean_text, needs_ocr, pdf_pages
from tenderlens.pipeline import (
    assemble_report, evaluate_extraction, run_eligibility, run_risks, summarize, verify,
)

logging.getLogger().setLevel(logging.INFO)

MAX_PAGES = 300
MAX_OCR_PAGES = 30


class TenderError(Exception):
    """A problem with the uploaded document; not worth retrying."""


def _pages(analysis_id: str) -> dict[int, str]:
    return {int(k): v for k, v in get_json(artifact(analysis_id, "pages")).items()}


def _ocr_page(data: bytes, page_number: int) -> str:
    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(data)).pages[page_number - 1])
    buf = io.BytesIO()
    writer.write(buf)
    result = boto3.client("textract").detect_document_text(Document={"Bytes": buf.getvalue()})
    return "\n".join(b["Text"] for b in result["Blocks"] if b["BlockType"] == "LINE")


def extract(event, _context):
    aid = event["analysis_id"]
    mark_step(aid, "extract")
    data = s3().get_object(Bucket=BUCKET, Key=event["tender_key"])["Body"].read()
    try:
        pages = pdf_pages(data)
    except Exception as err:  # noqa: BLE001
        raise TenderError(f"Couldn't open this PDF: {err}") from err
    if len(pages) > MAX_PAGES:
        raise TenderError(f"Tender has {len(pages)} pages; the limit is {MAX_PAGES}.")

    ocr_targets = [n for n, t in pages.items() if needs_ocr(t)][:MAX_OCR_PAGES]
    for n in ocr_targets:
        pages[n] = clean_text(_ocr_page(data, n))
    if sum(len(t) for t in pages.values()) < 200:
        raise TenderError("Couldn't read any text from this PDF.")

    put_json(artifact(aid, "pages"), pages)
    return {"pages": len(pages), "ocr_pages": len(ocr_targets)}


def eligibility(event, _context):
    aid = event["analysis_id"]
    mark_step(aid, "eligibility")
    out = run_eligibility(build_document(_pages(aid)))
    put_json(artifact(aid, "eligibility"), out)
    return out["meta"]


def risks(event, _context):
    aid = event["analysis_id"]
    mark_step(aid, "risks")
    out = run_risks(build_document(_pages(aid)))
    put_json(artifact(aid, "risks"), out)
    return out["meta"]


def verify_step(event, _context):
    aid = event["analysis_id"]
    mark_step(aid, "verify")
    verified = verify(get_json(artifact(aid, "eligibility")), get_json(artifact(aid, "risks")), _pages(aid))
    put_json(artifact(aid, "verified"), verified)
    return verified["grounding"]


def evaluate_step(event, _context):
    aid = event["analysis_id"]
    mark_step(aid, "evaluate")
    profile = load_profile(event["profile_id"])
    if profile is None:
        raise TenderError("Company profile not found.")
    evaluation = evaluate_extraction(get_json(artifact(aid, "verified")), profile, as_of=date.today())
    put_json(artifact(aid, "evaluation"), evaluation)
    return {"verdict": evaluation["verdict"]}


def summarize_step(event, _context):
    aid = event["analysis_id"]
    mark_step(aid, "summarize")
    profile = load_profile(event["profile_id"]) or {"name": "Your company"}
    summary = summarize(get_json(artifact(aid, "verified")), get_json(artifact(aid, "evaluation")), profile["name"])
    put_json(artifact(aid, "summary"), summary)
    return {"ok": True}


def save(event, _context):
    aid = event["analysis_id"]
    verified = get_json(artifact(aid, "verified"))
    profile = load_profile(event["profile_id"]) or {}
    extract_meta = event.get("extract", {})
    llm_meta = event.get("agents", [{}, {}])
    report = assemble_report(
        verified=verified,
        evaluation=get_json(artifact(aid, "evaluation")),
        summary=get_json(artifact(aid, "summary")),
        profile=profile,
        stats={
            "pages": extract_meta.get("pages"),
            "ocr_pages": extract_meta.get("ocr_pages"),
            "seconds": int(time.time()) - int(event.get("started_at", time.time())),
            "tokens": sum((m or {}).get("input_tokens", 0) + (m or {}).get("output_tokens", 0) for m in llm_meta),
            "model": (llm_meta[0] or {}).get("model"),
        },
    )
    put_json(artifact(aid, "report"), report)
    facts = report["key_facts"]
    table(ANALYSES_TABLE).update_item(
        Key={"id": aid},
        UpdateExpression="SET #s = :s, step = :step, verdict = :v, title = :t, organisation = :o, updated_at = :u",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues=to_ddb({":s": "DONE", ":step": "done", ":v": report["verdict"],
                                          ":t": facts.get("title"), ":o": facts.get("organisation"),
                                          ":u": int(time.time())}),
    )
    return {"verdict": report["verdict"]}


def fail(event, _context):
    aid = event["analysis_id"]
    error = event.get("error", {})
    cause = str(error.get("Cause", ""))
    message = "Analysis failed. Please try again."
    if error.get("Error") == "TenderError":
        try:
            import json
            message = json.loads(cause).get("errorMessage", message)
        except ValueError:
            pass
    table(ANALYSES_TABLE).update_item(
        Key={"id": aid},
        UpdateExpression="SET #s = :s, error = :e, updated_at = :u",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "FAILED", ":e": message, ":u": int(time.time())},
    )
    return {"failed": True}
