import pytest
from app.agents import compliance_agent
from app.config import settings
from app.models.schemas import Jurisdiction, LabelFacts, SelectedRule, Status
from app.services import rules


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "labelguard_mode", "mock")


def _selected(rule_id: str, applicable: bool, jurisdiction=Jurisdiction.india, reason="test") -> SelectedRule:
    pack = rules.load_rule_pack(jurisdiction)
    rule = next(r for r in pack.rules if r.rule_id == rule_id)
    return SelectedRule(rule=rule, applicable=applicable, applicability_reason=reason)


def test_not_applicable_rule_produces_not_applicable_finding_without_llm_call():
    selected = [_selected("RULE-IN-FOOD-010", applicable=False, reason="Not imported")]
    findings, usage = compliance_agent.run_compliance(LabelFacts(), selected)
    assert len(findings) == 1
    assert findings[0].status == Status.not_applicable
    assert findings[0].explanation == "Not imported"
    assert usage["total_tokens"] == 0


def test_physical_measurement_rule_auto_needs_review_without_llm_call():
    selected = [_selected("RULE-IN-FOOD-012", applicable=True)]
    findings, usage = compliance_agent.run_compliance(LabelFacts(), selected)
    assert len(findings) == 1
    assert findings[0].status == Status.needs_review
    assert usage["total_tokens"] == 0


def test_applicable_rule_goes_through_mock_llm_path():
    selected = [_selected("RULE-IN-FOOD-001", applicable=True)]
    findings, usage = compliance_agent.run_compliance(LabelFacts(), selected)
    assert len(findings) == 1
    assert findings[0].status == Status.needs_review
    assert "mock" in findings[0].explanation.lower()


def test_mixed_batch_produces_one_finding_per_rule():
    selected = [
        _selected("RULE-IN-FOOD-010", applicable=False, reason="not imported"),
        _selected("RULE-IN-FOOD-012", applicable=True),
        _selected("RULE-IN-FOOD-001", applicable=True),
    ]
    findings, _usage = compliance_agent.run_compliance(LabelFacts(), selected)
    assert len(findings) == 3
    statuses = {f.rule_id: f.status for f in findings}
    assert statuses["RULE-IN-FOOD-010"] == Status.not_applicable
    assert statuses["RULE-IN-FOOD-012"] == Status.needs_review
