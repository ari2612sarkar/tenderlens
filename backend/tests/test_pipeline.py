from datetime import date

from tenderlens.pipeline import evaluate_extraction, parse_bid_end, verify

PAGES = {
    1: "Bid Number: GEM/2026/B/1234\nBid End Date/Time 15-10-2026 15:00:00\n"
       "Minimum Average Annual Turnover of the bidder (For 3 Years) 50 Lakh (s)\n"
       "MSE Exemption for Years of Experience and Turnover Yes",
    2: "Liquidated damages at 0.5% per week without any upper limit.",
}

EXTRACTION = {
    "key_facts": {"tender_no": "GEM/2026/B/1234", "bid_end": "2026-10-15T15:00:00", "est_value_inr": None},
    "criteria": [
        {"id": "c1", "category": "turnover", "description": "Avg turnover 50L", "mandatory": True,
         "quote": "Minimum Average Annual Turnover of the bidder (For 3 Years) 50 Lakh (s)", "page": 1,
         "rule": {"type": "min_avg_turnover", "amount_inr": 5_000_000, "amount_text": "50 Lakh (s)", "last_n": 3}},
        {"id": "c2", "category": "certification", "description": "ISO 27001", "mandatory": True,
         "quote": "Bidder shall possess ISO 27001", "page": 1,
         "rule": {"type": "requires_cert", "any_of": ["ISO 27001"]}},
    ],
    "exemptions": [{"applies_to": "mse", "waives": ["experience", "turnover"],
                    "quote": "MSE Exemption for Years of Experience and Turnover Yes", "page": 1}],
    "documents_required": [],
}
RISKS = {"risks": [{"category": "liquidated_damages", "severity": "high", "title": "Uncapped LD",
                    "explanation": "x", "suggested_prebid_query": None,
                    "quote": "Liquidated damages at 0.5% per week without any upper limit.", "page": 2}]}

PROFILE = {"name": "Acme", "enterprise_size": "micro", "incorporation_year": 2023,
           "turnover_by_fy": {"2025-26": 10_00_000, "2024-25": 8_00_000, "2023-24": 5_00_000}}


def test_verify_flags_each_item_and_counts():
    v = verify(EXTRACTION, RISKS, PAGES)
    assert [c["grounded"] for c in v["criteria"]] == [True, False]
    assert v["exemptions"][0]["grounded"] is True
    assert v["risks"][0]["grounded"] is True
    assert v["grounding"] == {"checked": 4, "grounded": 3}


def test_evaluate_extraction_applies_grounded_exemption_and_flags_ungrounded():
    v = verify(EXTRACTION, RISKS, PAGES)
    ev = evaluate_extraction(v, PROFILE, as_of=date(2026, 10, 1))
    statuses = {r["criterion"]["id"]: r["status"] for r in ev["results"]}
    assert statuses == {"c1": "EXEMPT", "c2": "NEEDS_REVIEW"}
    assert ev["verdict"] == "CHECK_ITEMS"


def test_parse_bid_end_accepts_iso_and_date_only():
    assert parse_bid_end("2026-10-15T15:00:00").day == 15
    assert parse_bid_end("2026-10-15").month == 10
    assert parse_bid_end("15th October") is None
    assert parse_bid_end(None) is None
