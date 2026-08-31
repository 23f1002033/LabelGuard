from app.models.schemas import Finding, Jurisdiction, RulePack, RuleSource, Severity, Status
from app.services import report


def _pack():
    return RulePack(
        jurisdiction=Jurisdiction.india,
        jurisdiction_name="India",
        product_category="packaged_food",
        pack_version="test",
        sources=[RuleSource(source_id="S1", name="Test Source", url="https://example.com")],
        rules=[],
    )


def _finding(rule_id, status, severity=Severity.medium):
    return Finding(
        finding_id=f"{rule_id}-t",
        rule_id=rule_id,
        rule_reference="ref",
        requirement="req",
        status=status,
        severity=severity,
        explanation="explanation",
        confidence=0.9,
    )


def test_overall_pass_when_all_pass_or_not_applicable():
    findings = [
        _finding("R1", Status.passed),
        _finding("R2", Status.not_applicable),
    ]
    rpt = report.build_report(findings, _pack(), "Product", system="baseline")
    assert rpt.overall_status == "PASS"
    assert rpt.summary.compliance_score == 100.0


def test_overall_fail_when_any_fail_regardless_of_severity():
    findings = [
        _finding("R1", Status.passed),
        _finding("R2", Status.failed, severity=Severity.low),
    ]
    rpt = report.build_report(findings, _pack(), "Product", system="baseline")
    assert rpt.overall_status == "FAIL"
    assert rpt.summary.critical_failures == 0
    assert rpt.summary.failed == 1


def test_overall_needs_review_when_no_fail_but_uncertain():
    findings = [
        _finding("R1", Status.passed),
        _finding("R2", Status.needs_review),
    ]
    rpt = report.build_report(findings, _pack(), "Product", system="baseline")
    assert rpt.overall_status == "NEEDS_REVIEW"


def test_findings_sorted_fail_first_then_by_severity():
    findings = [
        _finding("LOW", Status.failed, severity=Severity.low),
        _finding("CRIT", Status.failed, severity=Severity.critical),
        _finding("PASS1", Status.passed),
    ]
    rpt = report.build_report(findings, _pack(), "Product", system="baseline")
    assert [f.rule_id for f in rpt.findings] == ["CRIT", "LOW", "PASS1"]


def test_compliance_score_ignores_not_applicable():
    findings = [
        _finding("R1", Status.passed),
        _finding("R2", Status.failed),
        _finding("R3", Status.not_applicable),
        _finding("R4", Status.not_applicable),
    ]
    rpt = report.build_report(findings, _pack(), "Product", system="baseline")
    assert rpt.summary.compliance_score == 50.0
