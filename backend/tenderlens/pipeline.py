"""Pipeline steps. Each takes and returns JSON-serialisable dicts so Step Functions can chain them."""

import json
import logging
from datetime import date, datetime

from tenderlens.agents.prompts import ELIGIBILITY_SYSTEM, RISK_SYSTEM, SUMMARY_SYSTEM
from tenderlens.agents.schemas import EligibilityOut, RisksOut, SummaryOut, to_criteria
from tenderlens.evaluate import evaluate_tender, fmt_inr
from tenderlens.grounding import ground_items
from tenderlens.models import CompanyProfile, Criterion, Exemption, RiskFlag

log = logging.getLogger(__name__)

VERDICT_TEXT = {
    "ELIGIBLE": "Eligible to bid",
    "ELIGIBLE_WITH_CAUTION": "Eligible, bid with caution",
    "CHECK_ITEMS": "Check items before bidding",
    "NOT_ELIGIBLE": "Not eligible",
    "CLOSED": "Bidding has closed",
}


def _user_message(document: str, task: str) -> str:
    return f"<tender>\n{document}\n</tender>\n\n{task}"


def run_eligibility(document: str) -> dict:
    from tenderlens.agents.llm import structured

    out, meta = structured(ELIGIBILITY_SYSTEM, _user_message(
        document, "Extract key facts, bidder eligibility criteria, MSE/startup exemptions and required documents."),
        EligibilityOut)
    return {
        "key_facts": out.key_facts.model_dump(),
        "criteria": [c.model_dump() for c in to_criteria(out.criteria)],
        "exemptions": [e.model_dump() for e in out.exemptions],
        "documents_required": [d.model_dump() for d in out.documents_required],
        "meta": meta,
    }


def run_risks(document: str) -> dict:
    from tenderlens.agents.llm import structured

    out, meta = structured(RISK_SYSTEM, _user_message(
        document, "Identify the risky clauses for a small bidder."), RisksOut)
    return {"risks": [r.model_dump() for r in out.risks], "meta": meta}


def verify(eligibility: dict, risks: dict, pages: dict[int, str]) -> dict:
    """Ground every cited item against the page text."""
    grounded = {
        "key_facts": eligibility.get("key_facts", {}),
        "criteria": ground_items(eligibility.get("criteria", []), pages),
        "exemptions": ground_items(eligibility.get("exemptions", []), pages),
        "documents_required": ground_items(eligibility.get("documents_required", []), pages),
        "risks": ground_items(risks.get("risks", []), pages),
    }
    items = [i for key in ("criteria", "exemptions", "documents_required", "risks") for i in grounded[key]]
    grounded["grounding"] = {"checked": len(items), "grounded": sum(1 for i in items if i["grounded"])}
    return grounded


def parse_bid_end(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def evaluate_extraction(verified: dict, profile: dict, as_of: date) -> dict:
    facts = verified.get("key_facts", {})
    evaluation = evaluate_tender(
        criteria=[Criterion.model_validate(c) for c in verified["criteria"]],
        exemptions=[Exemption.model_validate(e) for e in verified["exemptions"]],
        risks=[RiskFlag.model_validate(r) for r in verified["risks"]],
        profile=CompanyProfile.model_validate(profile),
        est_value_inr=facts.get("est_value_inr"),
        bid_end=parse_bid_end(facts.get("bid_end")),
        as_of=as_of,
    )
    return evaluation.model_dump()


def _fallback_summary(evaluation: dict, verified: dict) -> dict:
    failing = [r for r in evaluation["results"] if r["status"] in ("NOT_MET", "NEEDS_REVIEW", "MISSING_DATA")]
    reasons = "; ".join(f"{r['criterion']['description']}: {r['reason']}" for r in failing[:3])
    return {
        "headline": VERDICT_TEXT[evaluation["verdict"]],
        "summary": reasons or "All mandatory criteria are met or exempt.",
        "next_steps": ["Review each criterion and its source page.", "Prepare the listed documents.",
                       "Send pre-bid queries for high-risk clauses."],
    }


def summarize(verified: dict, evaluation: dict, profile_name: str) -> dict:
    """Plain-language summary written ONLY from the computed result. Never fails the pipeline."""
    facts = verified.get("key_facts", {})
    compact = {
        "company": profile_name,
        "tender": {k: facts.get(k) for k in ("title", "organisation", "bid_end")},
        "emd": fmt_inr(facts["emd_inr"]) if facts.get("emd_inr") else None,
        "emd_exempt": evaluation["emd_exempt"],
        "verdict": VERDICT_TEXT[evaluation["verdict"]],
        "criteria": [{"requirement": r["criterion"]["description"], "status": r["status"], "reason": r["reason"],
                      "mandatory": r["criterion"]["mandatory"]} for r in evaluation["results"]],
        "risks": [{"title": r["title"], "severity": r["severity"], "prebid_query": r.get("suggested_prebid_query")}
                  for r in verified["risks"] if r.get("grounded")][:6],
    }
    try:
        from tenderlens.agents.llm import structured

        out, _ = structured(SUMMARY_SYSTEM, json.dumps(compact, ensure_ascii=False), SummaryOut,
                            effort="low", max_tokens=4000)
        return out.model_dump()
    except Exception:  # noqa: BLE001 - the summary is a nicety; the report must still ship
        log.exception("summary failed; using fallback")
        return _fallback_summary(evaluation, verified)


def assemble_report(*, verified: dict, evaluation: dict, summary: dict, profile: dict, stats: dict) -> dict:
    return {
        "key_facts": verified.get("key_facts", {}),
        "verdict": evaluation["verdict"],
        "verdict_text": VERDICT_TEXT[evaluation["verdict"]],
        "summary": summary,
        "results": evaluation["results"],
        "counts": evaluation["counts"],
        "emd_exempt": evaluation["emd_exempt"],
        "exemptions": verified["exemptions"],
        "risks": verified["risks"],
        "documents_required": verified["documents_required"],
        "grounding": verified["grounding"],
        "profile": {"id": profile.get("id"), "name": profile.get("name")},
        "stats": stats,
        "analyzed_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
