import pytest
from app.agents import verification_agent
from app.agents.verification_agent import _result_from_raw
from app.config import settings
from app.models.schemas import CandidateFinding, Jurisdiction, LabelFacts, Severity, Status, Verdict
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


def test_missing_model_response_defaults_to_uncertain_needs_review():
    result = _result_from_raw("f1", None)
    assert result.verdict == Verdict.uncertain
    assert result.revised_status == Status.needs_review


def test_unknown_verdict_string_falls_back_to_uncertain():
    result = _result_from_raw("f1", {"verdict": "maybe", "reason": "unclear"})
    assert result.verdict == Verdict.uncertain
    assert result.revised_status == Status.needs_review


def test_confirmed_verdict_has_no_revised_status():
    result = _result_from_raw("f1", {"verdict": "confirmed", "reason": "evidence is solid"})
    assert result.verdict == Verdict.confirmed
    assert result.revised_status is None


def test_rejected_verdict_with_invalid_revised_status_falls_back_to_needs_review():
    result = _result_from_raw(
        "f1", {"verdict": "rejected", "reason": "evidence does not support it", "revised_status": "FAIL"}
    )
    assert result.verdict == Verdict.rejected
    assert result.revised_status == Status.needs_review


def test_rejected_verdict_with_valid_pass_is_honoured():
    result = _result_from_raw(
        "f1", {"verdict": "rejected", "reason": "actually present", "revised_status": "PASS"}
    )
    assert result.revised_status == Status.passed
