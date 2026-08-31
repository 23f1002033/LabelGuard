import pytest
from app.agents import verification_agent
from app.config import settings
from app.models.schemas import CandidateFinding, Jurisdiction, LabelFacts, Severity, Status
from app.services import rules


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "labelguard_mode", "mock")


def _rules_by_id():
    pack = rules.load_rule_pack(Jurisdiction.india)
    return {r.rule_id: r for r in pack.rules}


def _finding(rule_id, status, finding_id=None):
    return CandidateFinding(
        finding_id=finding_id or f"{rule_id}-t",
        rule_id=rule_id,
        status=status,
        severity=Severity.high,
        explanation="e",
        evidence=[],
        confidence=0.8,
    )


def test_only_fail_findings_are_sent_for_verification():
    findings = [
        _finding("RULE-IN-FOOD-001", Status.passed),
        _finding("RULE-IN-FOOD-002", Status.needs_review),
        _finding("RULE-IN-FOOD-003", Status.not_applicable),
    ]
    results, usage = verification_agent.run_verification(LabelFacts(), findings, _rules_by_id())
    assert results == []
    assert usage["total_tokens"] == 0


def test_fail_finding_gets_a_verification_result_in_mock_mode():
    findings = [_finding("RULE-IN-FOOD-001", Status.failed, finding_id="RULE-IN-FOOD-001-t")]
    results, _usage = verification_agent.run_verification(LabelFacts(), findings, _rules_by_id())
    assert len(results) == 1
    assert results[0].finding_id == "RULE-IN-FOOD-001-t"
    assert results[0].revised_status in (Status.passed, Status.needs_review)


def test_verification_never_produces_a_fail_revised_status():
    findings = [_finding(f"RULE-IN-FOOD-{i:03d}", Status.failed) for i in (1, 2, 4, 5)]
    results, _usage = verification_agent.run_verification(LabelFacts(), findings, _rules_by_id())
    for result in results:
        assert result.revised_status != Status.failed
        assert result.revised_status != Status.not_applicable
