"""Typed data shared by the agents, the grounding check and the rule engine."""

from datetime import date
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator

from tenderlens.fy import normalize_fy

EnterpriseSize = Literal["micro", "small", "medium", "large"]
ExemptClass = Literal["mse", "startup"]
Category = Literal[
    "turnover", "net_worth", "experience", "years_in_operation", "certification", "registration",
    "oem_authorization", "enterprise_size", "location", "sector", "other",
]
Waivable = Literal["emd", "turnover", "experience", "years_in_operation", "net_worth", "certification", "other"]
Status = Literal["MET", "NOT_MET", "EXEMPT", "NEEDS_REVIEW", "MISSING_DATA"]


# --- company profile ------------------------------------------------------------

class PastProject(BaseModel):
    title: str
    client_type: Literal["govt", "psu", "private"] = "govt"
    value_inr: int
    completed_year: int
    work_tags: list[str] = []


class CompanyProfile(BaseModel):
    id: str | None = None
    name: str
    enterprise_size: EnterpriseSize
    dpiit_startup: bool = False
    state: str = ""
    incorporation_year: int | None = None
    net_worth_inr: int | None = None
    employee_count: int | None = None
    turnover_by_fy: dict[str, int] = {}
    certifications: list[str] = []
    registrations: list[str] = []
    past_projects: list[PastProject] = []
    oem_authorizations: list[str] = []
    sector_tags: list[str] = []
    women_owned: bool = False
    sc_st_owned: bool = False

    @field_validator("turnover_by_fy")
    @classmethod
    def _normalize_fy_keys(cls, value: dict[str, int]) -> dict[str, int]:
        return {normalize_fy(k) or k: v for k, v in value.items()}

    @property
    def is_mse(self) -> bool:
        return self.enterprise_size in ("micro", "small")

    def years_in_operation(self, as_of: date) -> int | None:
        return None if self.incorporation_year is None else as_of.year - self.incorporation_year


# --- grounded extraction ------------------------------------------------------------

class Grounded(BaseModel):
    quote: str = Field(description="Verbatim text copied from the document that supports this item.")
    page: int = Field(description="Page number (from the [[PAGE n]] markers) where the quote appears.")
    grounded: bool | None = None


class MinAvgTurnover(BaseModel):
    type: Literal["min_avg_turnover"]
    amount_inr: int
    amount_text: str
    basis: Literal["average", "each_year"] = "average"
    fys: list[str] = []
    last_n: int | None = None


class MinNetWorth(BaseModel):
    type: Literal["min_net_worth"]
    amount_inr: int
    amount_text: str


class MinYearsInOp(BaseModel):
    type: Literal["min_years_in_op"]
    years: int


class SimilarWorkOption(BaseModel):
    count: int = 1
    min_value_inr: int | None = None
    min_value_text: str | None = None
    percent_of_estimate: float | None = None


class SimilarWork(BaseModel):
    type: Literal["similar_work"]
    options: list[SimilarWorkOption]
    within_years: int | None = None
    work_tags: list[str] = []
    definition_text: str = ""


class RequiresCert(BaseModel):
    type: Literal["requires_cert"]
    any_of: list[str]


class RequiresRegistration(BaseModel):
    type: Literal["requires_registration"]
    any_of: list[str]


class OemAuth(BaseModel):
    type: Literal["oem_auth"]
    brands: list[str] = []


class EnterpriseSizeRule(BaseModel):
    type: Literal["enterprise_size"]
    any_of: list[EnterpriseSize]


class LocationRule(BaseModel):
    type: Literal["location"]
    states: list[str]


class SectorRule(BaseModel):
    type: Literal["sector"]
    work_tags: list[str]


class Freeform(BaseModel):
    type: Literal["freeform"]
    text: str


Rule = Annotated[
    Union[MinAvgTurnover, MinNetWorth, MinYearsInOp, SimilarWork, RequiresCert, RequiresRegistration,
          OemAuth, EnterpriseSizeRule, LocationRule, SectorRule, Freeform],
    Field(discriminator="type"),
]


class Criterion(Grounded):
    id: str
    category: Category
    description: str
    mandatory: bool = True
    rule: Rule


class Exemption(Grounded):
    applies_to: ExemptClass
    waives: list[Waivable]


class RiskFlag(Grounded):
    category: Literal[
        "liquidated_damages", "payment_terms", "performance_security", "liability", "termination",
        "ip_ownership", "scope_ambiguity", "blacklisting", "other",
    ]
    severity: Literal["high", "medium", "low"]
    title: str
    explanation: str
    suggested_prebid_query: str | None = None


class DocRequired(Grounded):
    name: str
    reason: str = ""


class KeyFacts(BaseModel):
    tender_no: str | None = None
    organisation: str | None = None
    title: str | None = None
    bid_end: str | None = Field(None, description="ISO 8601 datetime, e.g. 2026-10-15T15:00:00")
    emd_inr: int | None = None
    est_value_inr: int | None = None
    pbg_pct: float | None = None
    contract_period: str | None = None


# --- evaluation output ------------------------------------------------------------

class CriterionResult(BaseModel):
    criterion: Criterion
    status: Status
    reason: str
    matched_projects: list[str] = []


class TenderEvaluation(BaseModel):
    verdict: Literal["CLOSED", "NOT_ELIGIBLE", "CHECK_ITEMS", "ELIGIBLE", "ELIGIBLE_WITH_CAUTION"]
    results: list[CriterionResult]
    emd_exempt: bool
    counts: dict[str, int]


class SchemeEvaluation(BaseModel):
    verdict: Literal["ELIGIBLE", "POSSIBLY_ELIGIBLE", "NOT_ELIGIBLE"]
    results: list[CriterionResult]
    counts: dict[str, int]
