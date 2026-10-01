from datetime import date

import pytest

from tenderlens.evaluate import evaluate_scheme, evaluate_tender
from tenderlens.models import CompanyProfile, Criterion, Exemption, RiskFlag

AS_OF = date(2026, 10, 1)


def profile(**overrides) -> CompanyProfile:
    base = dict(
        name="Acme Infotech",
        enterprise_size="small",
        dpiit_startup=False,
        state="Haryana",
        incorporation_year=2018,
        net_worth_inr=2_00_00_000,
        turnover_by_fy={"2025-26": 1_20_00_000, "2024-25": 1_00_00_000, "2023-24": 80_00_000},
        certifications=["ISO 9001:2015"],
        registrations=["GST", "PAN", "Udyam"],
        past_projects=[
            {"title": "HR portal for state PSU", "client_type": "psu", "value_inr": 45_00_000,
             "completed_year": 2025, "work_tags": ["software_development"]},
            {"title": "District e-office rollout", "client_type": "govt", "value_inr": 30_00_000,
             "completed_year": 2024, "work_tags": ["software_development", "it_support"]},
        ],
        sector_tags=["software_development"],
    )
    base.update(overrides)
    return CompanyProfile.model_validate(base)


def crit(rule: dict, *, category: str, mandatory: bool = True, grounded: bool = True, cid: str = "c1") -> Criterion:
    return Criterion.model_validate(
        dict(id=cid, category=category, description="test", mandatory=mandatory, rule=rule,
             quote="q", page=1, grounded=grounded)
    )


def turnover(amount_inr: int, amount_text: str, **kw) -> Criterion:
    return crit({"type": "min_avg_turnover", "amount_inr": amount_inr, "amount_text": amount_text, **kw},
                category="turnover")


def run(criteria, prof=None, exemptions=(), risks=(), est_value_inr=None, bid_end=None):
    return evaluate_tender(
        criteria=list(criteria), exemptions=list(exemptions), risks=list(risks),
        profile=prof or profile(), est_value_inr=est_value_inr, bid_end=bid_end, as_of=AS_OF,
    )


# --- turnover -------------------------------------------------------------

def test_average_turnover_met_over_last_three_completed_fys():
    result = run([turnover(1_00_00_000, "Rs. 1 Crore", last_n=3)]).results[0]
    assert result.status == "MET"  # avg of 1.2Cr, 1Cr, 0.8Cr = 1Cr


def test_average_turnover_not_met():
    result = run([turnover(1_50_00_000, "₹ 1.5 Crore", last_n=3)]).results[0]
    assert result.status == "NOT_MET"
    assert "1.5" in result.reason or "1,50,00,000" in result.reason


def test_turnover_each_year_basis_fails_if_any_year_below():
    result = run([turnover(90_00_000, "90 Lakh", last_n=3, basis="each_year")]).results[0]
    assert result.status == "NOT_MET"  # 2023-24 was 80 lakh


def test_turnover_missing_fy_is_missing_data():
    result = run([turnover(50_00_000, "50 Lakh", fys=["2022-23", "2023-24", "2024-25"])]).results[0]
    assert result.status == "MISSING_DATA"
    assert "2022-23" in result.reason


def test_turnover_amount_mismatch_needs_review():
    # model wrote 2.5 lakh but text says 2.5 crore
    result = run([turnover(2_50_000, "₹ 2.5 Crore", last_n=3)]).results[0]
    assert result.status == "NEEDS_REVIEW"


def test_turnover_fys_inferred_from_bid_end_not_today():
    # bid closed in Feb 2026 → last completed FYs are 2024-25, 2023-24, 2022-23
    from datetime import datetime
    result = run([turnover(50_00_000, "50 Lakh", last_n=3)], bid_end=datetime(2026, 2, 10)).results[0]
    assert result.status == "MISSING_DATA"


# --- other rule types -------------------------------------------------------

def test_similar_work_met_by_one_of_the_options():
    rule = {"type": "similar_work", "work_tags": ["software_development"], "within_years": 5,
            "definition_text": "software development for govt",
            "options": [{"count": 3, "percent_of_estimate": 0.4},
                        {"count": 2, "percent_of_estimate": 0.5},
                        {"count": 1, "percent_of_estimate": 0.8}]}
    result = run([crit(rule, category="experience")], est_value_inr=50_00_000).results[0]
    # 2 projects ≥ 25L (50% of 50L): 45L and 30L
    assert result.status == "MET"
    assert set(result.matched_projects) == {"HR portal for state PSU", "District e-office rollout"}


def test_similar_work_not_met_when_values_too_small():
    rule = {"type": "similar_work", "work_tags": ["software_development"],
            "definition_text": "x", "options": [{"count": 1, "min_value_inr": 80_00_000, "min_value_text": "80 Lakh"}]}
    assert run([crit(rule, category="experience")]).results[0].status == "NOT_MET"


def test_similar_work_ignores_unrelated_tags():
    rule = {"type": "similar_work", "work_tags": ["civil_works"], "definition_text": "x",
            "options": [{"count": 1, "min_value_inr": 1, "min_value_text": "Rs 1"}]}
    assert run([crit(rule, category="experience")]).results[0].status == "NOT_MET"


def test_similar_work_percent_without_estimate_needs_review():
    rule = {"type": "similar_work", "work_tags": ["software_development"], "definition_text": "x",
            "options": [{"count": 1, "percent_of_estimate": 0.8}]}
    assert run([crit(rule, category="experience")]).results[0].status == "NEEDS_REVIEW"


def test_similar_work_with_no_projects_in_profile_is_missing_data():
    rule = {"type": "similar_work", "work_tags": ["software_development"], "definition_text": "x",
            "options": [{"count": 1, "min_value_inr": 1, "min_value_text": "Rs 1"}]}
    assert run([crit(rule, category="experience")], prof=profile(past_projects=[])).results[0].status == "MISSING_DATA"


def test_certification_matches_ignoring_year_suffix():
    rule = {"type": "requires_cert", "any_of": ["ISO 9001"]}
    assert run([crit(rule, category="certification")]).results[0].status == "MET"


def test_missing_certification_not_met():
    rule = {"type": "requires_cert", "any_of": ["ISO 27001", "CMMI Level 3"]}
    assert run([crit(rule, category="certification")]).results[0].status == "NOT_MET"


def test_years_in_operation():
    rule = {"type": "min_years_in_op", "years": 5}
    assert run([crit(rule, category="years_in_operation")]).results[0].status == "MET"  # since 2018
    rule = {"type": "min_years_in_op", "years": 10}
    assert run([crit(rule, category="years_in_operation")]).results[0].status == "NOT_MET"


def test_net_worth_missing_is_missing_data():
    rule = {"type": "min_net_worth", "amount_inr": 1_00_00_000, "amount_text": "1 Crore"}
    result = run([crit(rule, category="net_worth")], prof=profile(net_worth_inr=None)).results[0]
    assert result.status == "MISSING_DATA"


def test_freeform_always_needs_review():
    rule = {"type": "freeform", "text": "Bidder must have an office in Bhubaneswar"}
    assert run([crit(rule, category="other")]).results[0].status == "NEEDS_REVIEW"


def test_ungrounded_criterion_needs_review_even_if_it_would_fail():
    result = run([crit({"type": "requires_cert", "any_of": ["ISO 27001"]}, category="certification",
                       grounded=False)]).results[0]
    assert result.status == "NEEDS_REVIEW"


# --- exemptions ---------------------------------------------------------------

def mse_exemption(waives, grounded=True):
    return Exemption.model_validate(dict(applies_to="mse", waives=waives, quote="q", page=1, grounded=grounded))


def test_mse_exemption_waives_failed_turnover():
    result = run([turnover(5_00_00_000, "5 Crore", last_n=3)], exemptions=[mse_exemption(["turnover"])])
    assert result.results[0].status == "EXEMPT"
    assert result.verdict == "ELIGIBLE"


def test_exemption_not_applied_to_medium_enterprise():
    result = run([turnover(5_00_00_000, "5 Crore", last_n=3)], prof=profile(enterprise_size="medium"),
                 exemptions=[mse_exemption(["turnover"])])
    assert result.results[0].status == "NOT_MET"


def test_ungrounded_exemption_is_ignored():
    result = run([turnover(5_00_00_000, "5 Crore", last_n=3)], exemptions=[mse_exemption(["turnover"], grounded=False)])
    assert result.results[0].status == "NOT_MET"


def test_startup_exemption_requires_dpiit_recognition():
    startup_ex = Exemption.model_validate(dict(applies_to="startup", waives=["experience"], quote="q", page=1, grounded=True))
    rule = {"type": "min_years_in_op", "years": 20}
    c = crit(rule, category="years_in_operation")
    assert run([c], exemptions=[startup_ex]).results[0].status == "NOT_MET"
    # experience waiver does not cover years_in_operation unless listed; use matching category
    startup_ex2 = Exemption.model_validate(dict(applies_to="startup", waives=["years_in_operation"], quote="q", page=1, grounded=True))
    assert run([c], prof=profile(dpiit_startup=True), exemptions=[startup_ex2]).results[0].status == "EXEMPT"


def test_emd_exemption_flag():
    assert run([], exemptions=[mse_exemption(["emd"])]).emd_exempt is True
    assert run([], exemptions=[mse_exemption(["emd"])], prof=profile(enterprise_size="large")).emd_exempt is False


# --- verdict ------------------------------------------------------------------

def test_verdict_not_eligible_when_mandatory_fails():
    assert run([turnover(5_00_00_000, "5 Crore", last_n=3)]).verdict == "NOT_ELIGIBLE"


def test_optional_criterion_does_not_affect_verdict():
    c = crit({"type": "requires_cert", "any_of": ["ISO 27001"]}, category="certification", mandatory=False)
    assert run([c]).verdict == "ELIGIBLE"


def test_verdict_check_items_when_review_needed():
    c = crit({"type": "freeform", "text": "x"}, category="other")
    assert run([c]).verdict == "CHECK_ITEMS"


def test_verdict_eligible_with_caution_on_grounded_high_risk():
    risk = RiskFlag.model_validate(dict(category="liquidated_damages", severity="high", title="Uncapped LD",
                                        explanation="x", quote="q", page=1, grounded=True))
    assert run([], risks=[risk]).verdict == "ELIGIBLE_WITH_CAUTION"


def test_ungrounded_high_risk_does_not_trigger_caution():
    risk = RiskFlag.model_validate(dict(category="liability", severity="high", title="x",
                                        explanation="x", quote="q", page=1, grounded=False))
    assert run([], risks=[risk]).verdict == "ELIGIBLE"


def test_verdict_closed_when_bid_end_passed():
    from datetime import datetime
    assert run([], bid_end=datetime(2026, 9, 1, 15, 0)).verdict == "CLOSED"


def test_counts_by_status():
    ev = run([turnover(1_00_00_000, "1 Crore", last_n=3, ), crit({"type": "freeform", "text": "x"}, category="other", cid="c2")])
    assert ev.counts == {"MET": 1, "NEEDS_REVIEW": 1}


# --- schemes -------------------------------------------------------------------

@pytest.mark.parametrize(
    "rules, expected",
    [
        ([{"type": "enterprise_size", "any_of": ["micro", "small"]}], "ELIGIBLE"),
        ([{"type": "enterprise_size", "any_of": ["micro"]}], "NOT_ELIGIBLE"),
        ([{"type": "location", "states": ["haryana", "punjab"]}], "ELIGIBLE"),
        ([{"type": "sector", "work_tags": ["manufacturing"]}], "NOT_ELIGIBLE"),
        ([{"type": "enterprise_size", "any_of": ["small"]}, {"type": "freeform", "text": "new unit"}], "POSSIBLY_ELIGIBLE"),
    ],
)
def test_scheme_verdicts(rules, expected):
    criteria = [crit(r, category="other", cid=f"s{i}") for i, r in enumerate(rules)]
    assert evaluate_scheme(criteria=criteria, profile=profile(), as_of=AS_OF).verdict == expected
