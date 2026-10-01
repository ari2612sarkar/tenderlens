from tenderlens.agents.schemas import CriterionOut, RuleSpec, to_criteria
from tenderlens.models import MinAvgTurnover, Freeform, SimilarWork


def out(rule: dict, **kw) -> CriterionOut:
    base = dict(category="turnover", description="Avg turnover 50L", mandatory=True, quote="q", page=3)
    base.update(kw)
    return CriterionOut(rule=RuleSpec(**rule), **base)


def test_flat_rule_becomes_typed_rule_and_gets_an_id():
    [c] = to_criteria([out({"type": "min_avg_turnover", "amount_inr": 5_000_000, "amount_text": "50 Lakh", "last_n": 3})])
    assert isinstance(c.rule, MinAvgTurnover)
    assert c.rule.last_n == 3
    assert c.id == "c1"
    assert c.page == 3


def test_null_fields_fall_back_to_model_defaults():
    [c] = to_criteria([out({"type": "min_avg_turnover", "amount_inr": 5_000_000, "amount_text": "50 Lakh",
                            "basis": None, "fys": None})])
    assert c.rule.basis == "average"
    assert c.rule.fys == []


def test_incomplete_rule_degrades_to_freeform_with_description():
    # min_avg_turnover without an amount can't be evaluated
    [c] = to_criteria([out({"type": "min_avg_turnover", "amount_text": "as per norms"})])
    assert isinstance(c.rule, Freeform)
    assert c.rule.text == "Avg turnover 50L"


def test_similar_work_options_survive_conversion():
    [c] = to_criteria([out({"type": "similar_work", "work_tags": ["software_development"],
                            "definition_text": "software", "options": [{"count": 3, "percent_of_estimate": 0.4}]},
                           category="experience")])
    assert isinstance(c.rule, SimilarWork)
    assert c.rule.options[0].percent_of_estimate == 0.4


def test_unknown_work_tags_are_dropped():
    [c] = to_criteria([out({"type": "sector", "work_tags": ["software_development", "space_lasers"]},
                           category="sector")])
    assert c.rule.work_tags == ["software_development"]
