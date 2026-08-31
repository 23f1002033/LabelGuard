from app.models.schemas import (
    ComplianceReport,
    Evidence,
    Finding,
    Jurisdiction,
    ReportSummary,
    RuleSource,
    Severity,
    Status,
)
from app.services.scoring import precision_recall_f1, score_case
from datetime import datetime, timezone


def _report(findings):
    return ComplianceReport(
        report_id="test",
        generated_at=datetime.now(timezone.utc),
        system="baseline",
        product_name="Test Product",
        jurisdiction=Jurisdiction.india,
        jurisdiction_name="India",
        product_category="packaged_food",
        overall_status="FAIL",
        summary=ReportSummary(passed=0, failed=0, needs_review=0, not_applicable=0, critical_failures=0, compliance_score=0.0),
        findings=findings,
        sources=[RuleSource(source_id="S1", name="Test", url="https://example.com")],
        disclaimer="test",
    )


def _finding(rule_id, status, snippet="", kind="ocr_text"):
    evidence = [Evidence(kind=kind, locator="x", snippet=snippet)] if snippet or kind == "vision_observation" else []
    return Finding(
        finding_id=f"{rule_id}-t",
        rule_id=rule_id,
        rule_reference="ref",
        requirement="req",
        status=status,
        severity=Severity.high,
        explanation="e",
        evidence=evidence,
        confidence=0.8,
    )


def test_true_positive_counts_matching_fail():
    annotation = {"expected_findings": [{"rule_id": "R1", "expected_status": "FAIL"}]}
    scores = score_case(_report([_finding("R1", Status.failed)]), annotation, raw_text="")
    assert scores["tp"] == 1
    assert scores["fp"] == 0
    assert scores["fn"] == 0


def test_false_negative_when_expected_fail_but_actual_pass():
    annotation = {"expected_findings": [{"rule_id": "R1", "expected_status": "FAIL"}]}
    scores = score_case(_report([_finding("R1", Status.passed)]), annotation, raw_text="")
    assert scores["fn"] == 1
    assert scores["tp"] == 0


def test_false_positive_when_expected_pass_but_actual_fail():
    annotation = {"expected_findings": [{"rule_id": "R1", "expected_status": "PASS"}]}
    scores = score_case(_report([_finding("R1", Status.failed)]), annotation, raw_text="")
    assert scores["fp"] == 1


def test_accept_also_prevents_false_positive():
    annotation = {
        "expected_findings": [
            {"rule_id": "R1", "expected_status": "NEEDS_REVIEW", "accept_also": ["PASS"]}
        ]
    }
    scores = score_case(_report([_finding("R1", Status.passed)]), annotation, raw_text="")
    assert scores["fp"] == 0
    assert scores["fn"] == 0


def test_missing_finding_counts_as_false_negative_for_expected_fail():
    annotation = {"expected_findings": [{"rule_id": "R1", "expected_status": "FAIL"}]}
    scores = score_case(_report([]), annotation, raw_text="")
    assert scores["fn"] == 1
    assert scores["coverage"] == 0


def test_evidence_grounded_on_literal_ocr_match():
    annotation = {"expected_findings": [{"rule_id": "R1", "expected_status": "PASS"}]}
    scores = score_case(
        _report([_finding("R1", Status.passed, snippet="Net Wt. 200 g")]),
        annotation,
        raw_text="Net Wt. 200 g and other text",
    )
    assert scores["evidence_grounded"] == 1
    assert scores["evidence_total"] == 1


def test_evidence_not_grounded_when_snippet_absent_from_ocr():
    annotation = {"expected_findings": [{"rule_id": "R1", "expected_status": "PASS"}]}
    scores = score_case(
        _report([_finding("R1", Status.passed, snippet="something never in the ocr text")]),
        annotation,
        raw_text="totally different text",
    )
    assert scores["evidence_grounded"] == 0
    assert scores["evidence_total"] == 1


def test_vision_observation_counts_as_grounded_even_without_text_match():
    annotation = {"expected_findings": [{"rule_id": "R1", "expected_status": "PASS"}]}
    scores = score_case(
        _report([_finding("R1", Status.passed, snippet="green circle symbol", kind="vision_observation")]),
        annotation,
        raw_text="no mention of any symbol",
    )
    assert scores["evidence_grounded"] == 1


def test_precision_recall_f1_basic():
    precision, recall, f1 = precision_recall_f1(tp=3, fp=1, fn=1)
    assert precision == 0.75
    assert recall == 0.75
    assert f1 == 0.75


def test_precision_recall_f1_handles_zero_division():
    assert precision_recall_f1(0, 0, 0) == (0.0, 0.0, 0.0)
