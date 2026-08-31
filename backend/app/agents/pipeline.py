from __future__ import annotations

import time

from app.agents import compliance_agent, extraction_agent, retrieval_agent, verification_agent
from app.models.schemas import ComplianceReport, Finding, ProductContext, Status
from app.services import ocr, report, rules
from app.services.trace import TraceRecorder


def _merge_usage(*usages: dict) -> dict:
    total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for usage in usages:
        for key in total:
            total[key] += usage.get(key, 0)
    return total


def _build_findings(candidate_findings, verification_by_finding_id, pack) -> list[Finding]:
    source_lookup = rules.source_lookup(pack)
    rules_by_id = {r.rule_id: r for r in pack.rules}
    findings = []
    for candidate in candidate_findings:
        rule = rules_by_id[candidate.rule_id]
        source_name, source_url = source_lookup.get(rule.source_id, ("", ""))
        verification = verification_by_finding_id.get(candidate.finding_id)

        final_status = candidate.status
        if verification and verification.revised_status:
            final_status = verification.revised_status

        findings.append(
            Finding(
                finding_id=candidate.finding_id,
                rule_id=candidate.rule_id,
                rule_reference=rule.source_reference,
                requirement=rule.requirement,
                status=final_status,
                severity=candidate.severity,
                explanation=candidate.explanation,
                evidence=candidate.evidence,
                confidence=candidate.confidence,
                suggested_fix=candidate.suggested_fix,
                verification=verification,
                source_name=source_name,
                source_url=source_url,
            )
        )
    return findings


def run_agent(
    image_bytes: bytes,
    context: ProductContext,
    case_id: str | None = None,
    mime_type: str = "image/png",
) -> tuple[ComplianceReport, TraceRecorder]:
    start = time.monotonic()
    trace = TraceRecorder(system="agent", case_id=case_id)

    pack = rules.load_rule_pack(context.jurisdiction)
    trace.log("pipeline", "load_rule_pack", result=f"{len(pack.rules)} rules loaded", tool_used="rules.load_rule_pack")

    raw_text = ocr.extract_text(image_bytes)
    facts, extraction_usage = extraction_agent.run_extraction(image_bytes, raw_text, mime_type)
    present_count = sum(1 for f in facts.fields.values() if f.present)
    trace.log(
        "extraction_agent",
        "extract_label_fields",
        tool_used="pytesseract + vision_model",
        result=f"Extracted label fields: {present_count}/{len(facts.fields)} fields present",
    )

    selected_rules, signals = retrieval_agent.select_rules(pack, facts, context)
    applicable_count = sum(1 for sr in selected_rules if sr.applicable)
    trace.log(
        "retrieval_agent",
        "select_applicable_rules",
        tool_used="deterministic_applicability_engine",
        result=f"Selected applicable rules: {applicable_count}/{len(selected_rules)} rules apply",
        decision=f"signals: {signals.model_dump()}",
    )

    candidate_findings, compliance_usage = compliance_agent.run_compliance(facts, selected_rules)
    fail_count = sum(1 for f in candidate_findings if f.status == Status.failed)
    trace.log(
        "compliance_agent",
        "generate_candidate_findings",
        tool_used="llm",
        result=f"Generated candidate findings: {len(candidate_findings)} findings, {fail_count} candidate FAIL",
    )

    rules_by_id = {r.rule_id: r for r in pack.rules}
    verification_results, verification_usage = verification_agent.run_verification(
        facts, candidate_findings, rules_by_id
    )
    rejected_count = sum(1 for v in verification_results if v.verdict.value == "rejected")
    trace.log(
        "verification_agent",
        "verify_findings",
        tool_used="llm",
        result=f"Verified findings: {len(verification_results)} FAIL findings challenged, {rejected_count} rejected",
    )

    verification_by_finding_id = {v.finding_id: v for v in verification_results}
    findings = _build_findings(candidate_findings, verification_by_finding_id, pack)

    product_name = None
    name_field = facts.get("product_name")
    if name_field and name_field.present:
        product_name = str(name_field.value)

    runtime = time.monotonic() - start
    usage = _merge_usage(extraction_usage, compliance_usage, verification_usage)
    compliance_report = report.build_report(
        findings,
        pack,
        product_name,
        system="agent",
        runtime_seconds=runtime,
        token_usage=usage,
    )
    trace.log(
        "pipeline",
        "generate_final_report",
        result=compliance_report.overall_status,
        duration_ms=int(runtime * 1000),
    )
    trace.save()
    return compliance_report, trace
