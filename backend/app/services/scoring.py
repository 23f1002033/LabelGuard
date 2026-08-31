from __future__ import annotations

from app.models.schemas import ComplianceReport, Status

FLAGGED_STATUSES = {Status.failed.value, Status.needs_review.value}


def score_case(report: ComplianceReport, annotation: dict, raw_text: str) -> dict:
    findings_by_rule = {f.rule_id: f for f in report.findings}
    expected_by_rule = {e["rule_id"]: e for e in annotation["expected_findings"]}

    tp = fp = fn = 0
    flagged_tp = flagged_fp = flagged_fn = 0
    status_matches = 0
    status_total = 0
    applicability_correct = 0
    applicability_total = 0
    evidence_grounded = 0
    evidence_total = 0
    covered = 0
    detail = []

    for rule_id, expected in expected_by_rule.items():
        expected_status = expected["expected_status"]
        accept_also = set(expected.get("accept_also", []))
        accepted = {expected_status} | accept_also

        finding = findings_by_rule.get(rule_id)
        actual_status = finding.status.value if finding else None
        if finding is not None:
            covered += 1

        status_total += 1
        accepted_match = actual_status in accepted
        if actual_status == expected_status:
            status_matches += 1

        if expected_status == "NOT_APPLICABLE":
            applicability_total += 1
            if accepted_match:
                applicability_correct += 1

        if expected_status == "FAIL":
            if actual_status == "FAIL":
                tp += 1
            elif not accepted_match:
                fn += 1
        else:
            if actual_status == "FAIL" and not accepted_match:
                fp += 1

        if expected_status in FLAGGED_STATUSES:
            if accepted_match and actual_status in FLAGGED_STATUSES:
                flagged_tp += 1
            elif not accepted_match:
                flagged_fn += 1
        else:
            if actual_status in FLAGGED_STATUSES and not accepted_match:
                flagged_fp += 1

        if finding and finding.evidence:
            evidence_total += 1
            evidence = finding.evidence[0]
            snippet = evidence.snippet.lower().strip()
            if evidence.kind == "absence" and finding.status.value in ("FAIL", "NEEDS_REVIEW"):
                evidence_grounded += 1
            elif evidence.kind == "vision_observation":
                evidence_grounded += 1
            elif snippet and snippet in raw_text.lower():
                evidence_grounded += 1

        detail.append(
            {
                "rule_id": rule_id,
                "expected": expected_status,
                "accept_also": sorted(accept_also),
                "actual": actual_status,
                "accepted_match": accepted_match,
            }
        )

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "flagged_tp": flagged_tp,
        "flagged_fp": flagged_fp,
        "flagged_fn": flagged_fn,
        "status_matches": status_matches,
        "status_total": status_total,
        "applicability_correct": applicability_correct,
        "applicability_total": applicability_total,
        "evidence_grounded": evidence_grounded,
        "evidence_total": evidence_total,
        "coverage": covered,
        "coverage_total": len(expected_by_rule),
        "detail": detail,
    }


def precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return round(precision, 3), round(recall, 3), round(f1, 3)
