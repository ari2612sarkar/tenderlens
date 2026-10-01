"""Model-facing output schemas.

These are deliberately flat and simple (structured outputs work best that way). `to_criteria`
converts them into the strict typed rules the engine evaluates, degrading anything incomplete
to a `freeform` rule so it surfaces as "Needs review" instead of being guessed at.
"""

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from tenderlens.models import (
    Category, Criterion, EnterpriseSize, ExemptClass, KeyFacts, SimilarWorkOption, Waivable,
)
from tenderlens.taxonomy import WORK_TAGS

_TAGS_HELP = "Allowed values: " + ", ".join(WORK_TAGS)


class Cited(BaseModel):
    quote: str = Field(description="Exact verbatim text copied from ONE page of the document (max ~300 characters).")
    page: int = Field(description="The page number from the [[PAGE n]] marker where the quote appears.")


class RuleSpec(BaseModel):
    type: Literal[
        "min_avg_turnover", "min_net_worth", "min_years_in_op", "similar_work", "requires_cert",
        "requires_registration", "oem_auth", "enterprise_size", "location", "sector", "freeform",
    ]
    amount_inr: int | None = Field(None, description="Amount in whole rupees (1 lakh = 100000, 1 crore = 10000000).")
    amount_text: str | None = Field(None, description="The amount exactly as written in the document, e.g. '50 Lakh (s)'.")
    basis: Literal["average", "each_year"] | None = None
    fys: list[str] | None = Field(None, description="Explicit financial years if listed, e.g. ['2022-23', '2023-24'].")
    last_n: int | None = Field(None, description="'Last N financial years' when years are not listed explicitly.")
    years: int | None = None
    options: list[SimilarWorkOption] | None = Field(
        None, description="Alternative ways to satisfy similar-work experience, e.g. 3 works of 40% / 2 of 50% / 1 of 80%. "
                          "Use percent_of_estimate as a fraction (0.4) when the value is relative to estimated cost.")
    within_years: int | None = None
    work_tags: list[str] | None = Field(None, description=_TAGS_HELP)
    definition_text: str | None = None
    any_of: list[str] | None = None
    brands: list[str] | None = None
    states: list[str] | None = None
    text: str | None = None


class CriterionOut(Cited):
    category: Category
    description: str = Field(description="One plain-English line, e.g. 'Average annual turnover of ₹50 lakh over 3 years'.")
    mandatory: bool = True
    rule: RuleSpec


class ExemptionOut(Cited):
    applies_to: ExemptClass
    waives: list[Waivable]


class DocOut(Cited):
    name: str
    reason: str = ""


class EligibilityOut(BaseModel):
    key_facts: KeyFacts
    criteria: list[CriterionOut]
    exemptions: list[ExemptionOut]
    documents_required: list[DocOut]


class RiskOut(Cited):
    category: Literal[
        "liquidated_damages", "payment_terms", "performance_security", "liability", "termination",
        "ip_ownership", "scope_ambiguity", "blacklisting", "other",
    ]
    severity: Literal["high", "medium", "low"]
    title: str
    explanation: str = Field(description="Why this matters to a small business owner, in 1-2 plain sentences.")
    suggested_prebid_query: str | None = Field(
        None, description="A polite clarification/relaxation request the bidder could submit at the pre-bid stage.")


class RisksOut(BaseModel):
    risks: list[RiskOut]


class SummaryOut(BaseModel):
    headline: str
    summary: str
    next_steps: list[str]


class SchemeOut(BaseModel):
    """Eligibility rules for a government scheme (reuses the tender criterion shape)."""
    name: str
    benefit: str
    criteria: list[CriterionOut]


def to_criteria(outs: list[CriterionOut]) -> list[Criterion]:
    criteria = []
    for i, o in enumerate(outs, start=1):
        spec = {k: v for k, v in o.rule.model_dump().items() if v is not None}
        if "work_tags" in spec:
            spec["work_tags"] = [t for t in spec["work_tags"] if t in WORK_TAGS]
        base = dict(id=f"c{i}", category=o.category, description=o.description, mandatory=o.mandatory,
                    quote=o.quote, page=o.page)
        try:
            criteria.append(Criterion.model_validate({**base, "rule": spec}))
        except ValidationError:
            criteria.append(Criterion.model_validate({**base, "rule": {"type": "freeform", "text": o.description}}))
    return criteria


__all__ = [
    "CriterionOut", "DocOut", "EligibilityOut", "EnterpriseSize", "ExemptionOut", "RiskOut", "RisksOut",
    "RuleSpec", "SchemeOut", "SummaryOut", "to_criteria",
]
