"""Deterministic rule engine: typed criteria x company profile -> statuses and a verdict.

No LLM calls here. Everything the model extracted is treated as a claim; this module
decides what it means for a specific company.
"""

import re
from collections import Counter
from datetime import date, datetime

from tenderlens.amounts import amounts_agree
from tenderlens.fy import last_completed_fys, normalize_fy
from tenderlens.models import (
    CompanyProfile, Criterion, CriterionResult, Exemption, RiskFlag, SchemeEvaluation, TenderEvaluation,
)

_UNRESOLVED = ("NOT_MET", "MISSING_DATA", "NEEDS_REVIEW")


def fmt_inr(amount: float) -> str:
    for size, suffix in ((10_000_000, "Cr"), (100_000, "L")):
        if amount >= size:
            return f"₹{f'{amount / size:.2f}'.rstrip('0').rstrip('.')} {suffix}"
    return f"₹{amount:,.0f}"


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _first_match(have: list[str], want: list[str]) -> str | None:
    for w in want:
        wk = _key(w)
        for h in have:
            hk = _key(h)
            if wk and hk and (wk in hk or hk in wk):
                return h
    return None


def _check(c: Criterion, p: CompanyProfile, est_value_inr: int | None, fy_anchor: date, as_of: date):
    """Return (status, reason, matched_projects) for one criterion, ignoring exemptions."""
    r = c.rule
    if c.grounded is False:
        return "NEEDS_REVIEW", "Couldn't find this text on the cited page. Verify it in the tender.", []

    if r.type == "min_avg_turnover":
        if not amounts_agree(r.amount_inr, r.amount_text):
            return "NEEDS_REVIEW", f"Couldn't confirm the required amount ('{r.amount_text}').", []
        fys = [f for f in (normalize_fy(x) for x in r.fys) if f] or last_completed_fys(r.last_n or 3, fy_anchor)
        missing = [f for f in fys if f not in p.turnover_by_fy]
        if missing:
            return "MISSING_DATA", f"Add turnover for FY {', '.join(missing)} to your profile.", []
        values = [p.turnover_by_fy[f] for f in fys]
        span = f"FY {fys[-1]} to {fys[0]}" if len(fys) > 1 else f"FY {fys[0]}"
        if r.basis == "each_year":
            low = min(values)
            ok = low >= r.amount_inr
            return ("MET" if ok else "NOT_MET"), (
                f"Lowest yearly turnover {fmt_inr(low)} ({span}) {'≥' if ok else '<'} required {fmt_inr(r.amount_inr)}."), []
        avg = sum(values) / len(values)
        ok = avg >= r.amount_inr
        return ("MET" if ok else "NOT_MET"), (
            f"Average turnover {fmt_inr(avg)} ({span}) {'≥' if ok else '<'} required {fmt_inr(r.amount_inr)}."), []

    if r.type == "min_net_worth":
        if not amounts_agree(r.amount_inr, r.amount_text):
            return "NEEDS_REVIEW", f"Couldn't confirm the required amount ('{r.amount_text}').", []
        if p.net_worth_inr is None:
            return "MISSING_DATA", "Add net worth to your profile.", []
        ok = p.net_worth_inr >= r.amount_inr
        return ("MET" if ok else "NOT_MET"), (
            f"Net worth {fmt_inr(p.net_worth_inr)} {'≥' if ok else '<'} required {fmt_inr(r.amount_inr)}."), []

    if r.type == "min_years_in_op":
        years = p.years_in_operation(as_of)
        if years is None:
            return "MISSING_DATA", "Add your incorporation year to your profile.", []
        ok = years >= r.years
        return ("MET" if ok else "NOT_MET"), f"{years} years in operation (needs {r.years}).", []

    if r.type == "similar_work":
        if not p.past_projects:
            return "MISSING_DATA", "Add past projects to your profile.", []
        if not r.work_tags:
            return "NEEDS_REVIEW", "Couldn't map the tender's definition of 'similar work' to a work category.", []
        min_year = fy_anchor.year - r.within_years if r.within_years else None
        similar = [pr for pr in p.past_projects
                   if set(pr.work_tags) & set(r.work_tags) and (min_year is None or pr.completed_year >= min_year)]
        unresolved = False
        for opt in r.options:
            if opt.percent_of_estimate is not None:
                if est_value_inr is None:
                    unresolved = True
                    continue
                pct = opt.percent_of_estimate / 100 if opt.percent_of_estimate > 1 else opt.percent_of_estimate
                threshold = pct * est_value_inr
            elif opt.min_value_inr is not None:
                if opt.min_value_text and not amounts_agree(opt.min_value_inr, opt.min_value_text):
                    unresolved = True
                    continue
                threshold = opt.min_value_inr
            else:
                threshold = 0
            qualifying = [pr for pr in similar if pr.value_inr >= threshold]
            if len(qualifying) >= opt.count:
                return "MET", (f"{len(qualifying)} similar project(s) worth ≥ {fmt_inr(threshold)} "
                               f"(needs {opt.count})."), [pr.title for pr in qualifying]
        if unresolved:
            return "NEEDS_REVIEW", "Couldn't resolve the value threshold (estimated value or amount unclear).", []
        if not similar:
            return "NOT_MET", "No similar past projects in your profile.", []
        return "NOT_MET", f"{len(similar)} similar project(s), but none meet the count/value thresholds.", []

    if r.type in ("requires_cert", "requires_registration", "oem_auth"):
        have = {"requires_cert": p.certifications, "requires_registration": p.registrations,
                "oem_auth": p.oem_authorizations}[r.type]
        want = r.brands if r.type == "oem_auth" else r.any_of
        if not want:
            return "NEEDS_REVIEW", "Requirement is unspecific. Check the tender.", []
        hit = _first_match(have, want)
        if hit:
            return "MET", f"Profile has {hit}.", []
        return "NOT_MET", f"Profile lists none of: {', '.join(want)}.", []

    if r.type == "enterprise_size":
        ok = p.enterprise_size in r.any_of
        return ("MET" if ok else "NOT_MET"), f"Enterprise size is {p.enterprise_size} (needs {'/'.join(r.any_of)}).", []

    if r.type == "location":
        states = [s.strip().lower() for s in r.states]
        if not p.state:
            return "MISSING_DATA", "Add your state to your profile.", []
        ok = p.state.strip().lower() in states
        return ("MET" if ok else "NOT_MET"), f"Located in {p.state} (eligible: {', '.join(r.states)}).", []

    if r.type == "sector":
        ok = bool(set(p.sector_tags) & set(r.work_tags))
        return ("MET" if ok else "NOT_MET"), f"Sector {'matches' if ok else 'does not match'} ({', '.join(r.work_tags)}).", []

    return "NEEDS_REVIEW", f"Check manually: {r.text}", []


def _applicable_exemption(category: str, p: CompanyProfile, exemptions: list[Exemption]) -> Exemption | None:
    for ex in exemptions:
        if ex.grounded is False or category not in ex.waives:
            continue
        if (ex.applies_to == "mse" and p.is_mse) or (ex.applies_to == "startup" and p.dpiit_startup):
            return ex
    return None


def evaluate_criteria(criteria: list[Criterion], profile: CompanyProfile, exemptions: list[Exemption],
                      est_value_inr: int | None, fy_anchor: date, as_of: date) -> list[CriterionResult]:
    results = []
    for c in criteria:
        status, reason, matched = _check(c, profile, est_value_inr, fy_anchor, as_of)
        if status in _UNRESOLVED:
            ex = _applicable_exemption(c.category, profile, exemptions)
            if ex:
                who = "micro & small enterprises" if ex.applies_to == "mse" else "DPIIT-recognised startups"
                status, reason = "EXEMPT", f"Waived for {who} (page {ex.page})."
        results.append(CriterionResult(criterion=c, status=status, reason=reason, matched_projects=matched))
    return results


def _counts(results: list[CriterionResult]) -> dict[str, int]:
    return dict(Counter(r.status for r in results))


def evaluate_tender(*, criteria: list[Criterion], exemptions: list[Exemption], risks: list[RiskFlag],
                    profile: CompanyProfile, est_value_inr: int | None, bid_end: datetime | None,
                    as_of: date) -> TenderEvaluation:
    fy_anchor = bid_end.date() if bid_end else as_of
    results = evaluate_criteria(criteria, profile, exemptions, est_value_inr, fy_anchor, as_of)
    mandatory = {r.status for r in results if r.criterion.mandatory}

    if bid_end and bid_end.date() < as_of:
        verdict = "CLOSED"
    elif "NOT_MET" in mandatory:
        verdict = "NOT_ELIGIBLE"
    elif mandatory & {"NEEDS_REVIEW", "MISSING_DATA"}:
        verdict = "CHECK_ITEMS"
    elif any(r.severity == "high" and r.grounded is not False for r in risks):
        verdict = "ELIGIBLE_WITH_CAUTION"
    else:
        verdict = "ELIGIBLE"

    return TenderEvaluation(
        verdict=verdict,
        results=results,
        emd_exempt=_applicable_exemption("emd", profile, exemptions) is not None,
        counts=_counts(results),
    )


def evaluate_scheme(*, criteria: list[Criterion], profile: CompanyProfile, as_of: date) -> SchemeEvaluation:
    results = evaluate_criteria(criteria, profile, [], None, as_of, as_of)
    mandatory = {r.status for r in results if r.criterion.mandatory}
    if "NOT_MET" in mandatory:
        verdict = "NOT_ELIGIBLE"
    elif mandatory & {"NEEDS_REVIEW", "MISSING_DATA"}:
        verdict = "POSSIBLY_ELIGIBLE"
    else:
        verdict = "ELIGIBLE"
    return SchemeEvaluation(verdict=verdict, results=results, counts=_counts(results))
