import pytest
from app.agents import compliance_agent
from app.agents.compliance_agent import _evidence, _finding_from_raw
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


def test_evidence_mapping_marks_absence_snippets_correctly():
    evidence = _evidence("No allergen statement was found on the label")
    assert len(evidence) == 1
    assert evidence[0].kind == "absence"


def test_evidence_mapping_marks_positive_findings_as_fact():
    evidence = _evidence("Net Wt. 200 g is printed on the front panel")
    assert len(evidence) == 1
    assert evidence[0].kind == "fact"


def test_evidence_mapping_empty_snippet_produces_no_evidence():
    assert _evidence("") == []
    assert _evidence(None) == []


def test_finding_from_raw_missing_response_defaults_to_needs_review():
    pack = rules.load_rule_pack(Jurisdiction.india)
    rule = next(r for r in pack.rules if r.rule_id == "RULE-IN-FOOD-001")
    finding = _finding_from_raw(rule, None)
    assert finding.status == Status.needs_review
    assert finding.confidence == 0.0
    assert "did not return a verdict" in finding.explanation


def test_finding_from_raw_rejects_not_applicable_from_model():
    pack = rules.load_rule_pack(Jurisdiction.india)
    rule = next(r for r in pack.rules if r.rule_id == "RULE-IN-FOOD-001")
    finding = _finding_from_raw(rule, {"status": "NOT_APPLICABLE", "explanation": "trying to sneak past retrieval"})
    assert finding.status == Status.needs_review


def test_finding_from_raw_clamps_out_of_range_confidence():
    pack = rules.load_rule_pack(Jurisdiction.india)
    rule = next(r for r in pack.rules if r.rule_id == "RULE-IN-FOOD-001")
    finding = _finding_from_raw(rule, {"status": "PASS", "confidence": 42})
    assert finding.confidence == 1.0
