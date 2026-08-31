from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.schemas import (
    ComplianceReport,
    Finding,
    Jurisdiction,
    ReportSummary,
    RulePack,
    Severity,
    Status,
)

_SEVERITY_ORDER = {Severity.critical: 0, Severity.high: 1, Severity.medium: 2, Severity.low: 3}
_STATUS_ORDER = {Status.failed: 0, Status.needs_review: 1, Status.passed: 2, Status.not_applicable: 3}

DISCLAIMER = (
    "This report is an AI-assisted preliminary compliance review. It is not legal "
    "advice and does not replace review by a qualified professional or regulator. "
    "This rule pack covers a bounded subset of labelling requirements and is not a "
    "complete statement of the law in this jurisdiction."
)


def build_report(
    findings: list[Finding],
    rule_pack: RulePack,
    product_name: str | None,
    system: str,
    runtime_seconds: float | None = None,
    token_usage: dict[str, int] | None = None,
) -> ComplianceReport:
    passed = sum(1 for f in findings if f.status == Status.passed)
    failed = sum(1 for f in findings if f.status == Status.failed)
    needs_review = sum(1 for f in findings if f.status == Status.needs_review)
    not_applicable = sum(1 for f in findings if f.status == Status.not_applicable)
    critical_failures = sum(
        1 for f in findings if f.status == Status.failed and f.severity == Severity.critical
    )

    evaluated = passed + failed + needs_review
    compliance_score = round((passed / evaluated) * 100, 1) if evaluated else 0.0

    if failed > 0:
        overall_status = "FAIL"
    elif needs_review > 0:
        overall_status = "NEEDS_REVIEW"
    else:
        overall_status = "PASS"

    return ComplianceReport(
        report_id=str(uuid.uuid4()),
        generated_at=datetime.now(timezone.utc),
        system=system,
        product_name=product_name,
        jurisdiction=rule_pack.jurisdiction,
        jurisdiction_name=rule_pack.jurisdiction_name,
        product_category=rule_pack.product_category,
        overall_status=overall_status,
        summary=ReportSummary(
            passed=passed,
            failed=failed,
            needs_review=needs_review,
            not_applicable=not_applicable,
            critical_failures=critical_failures,
            compliance_score=compliance_score,
        ),
        findings=sorted(
            findings,
            key=lambda f: (_STATUS_ORDER[f.status], _SEVERITY_ORDER[f.severity], f.rule_id),
        ),
        sources=rule_pack.sources,
        disclaimer=DISCLAIMER,
        runtime_seconds=runtime_seconds,
        token_usage=token_usage or {},
    )
