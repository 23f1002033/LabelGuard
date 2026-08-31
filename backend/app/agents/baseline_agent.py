from __future__ import annotations

import time

from app.models.schemas import (
    ComplianceReport,
    Evidence,
    Finding,
    ProductContext,
    Rule,
    RulePack,
    Status,
)
from app.config import settings
from app.services import llm_client, ocr, report, rules
from app.services.trace import TraceRecorder

_STATUS_VALUES = {s.value for s in Status}


def _mock_response(pack: RulePack) -> tuple[dict, dict]:
    findings = [
        {
            "rule_id": r.rule_id,
            "status": "NEEDS_REVIEW",
            "explanation": "LABELGUARD_MODE=mock, no live model call was made for this case.",
            "evidence_snippet": "",
            "confidence": 0.0,
            "suggested_fix": r.suggested_fix,
        }
        for r in pack.rules
    ]
    parsed = {"product_name": None, "findings": findings}
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return parsed, usage


def _rules_context(pack: RulePack) -> str:
    lines = []
    for r in pack.rules:
        conditions = "; ".join(
            f"{c.fact} {c.operator} {c.value if c.value is not None else ''}".strip()
            for c in r.applicability.conditions
        )
        lines.append(
            f"- {r.rule_id} [{r.severity.value}] {r.category}: {r.requirement}\n"
            f"  applies_when: {'always' if r.applicability.always_applies else r.applicability.summary}"
            + (f" ({conditions})" if conditions else "")
            + f"\n  source: {r.source_reference}"
        )
    return "\n".join(lines)


def _build_messages(pack: RulePack, ocr_text: str, context: ProductContext, image_data_url: str) -> list[dict]:
    system_prompt = (
        "You are a food label compliance checker. You are given a photo of a packaged "
        "food label, the text an OCR engine extracted from it, and a list of mandatory "
        f"labelling requirements for {pack.jurisdiction_name}. "
        "For every requirement, decide whether the label satisfies it. "
        "Use status PASS if the label clearly satisfies it, FAIL if it clearly does not, "
        "NEEDS_REVIEW if you cannot tell confidently, NOT_APPLICABLE if the requirement "
        "does not apply to this product based on the applies_when condition. "
        "Never claim a field is present unless you can see or read it. If evidence is "
        "missing, say so plainly instead of guessing. "
        "Respond with a JSON object: "
        '{"product_name": string or null, "findings": ['
        '{"rule_id": string, "status": "PASS|FAIL|NEEDS_REVIEW|NOT_APPLICABLE", '
        '"explanation": string, "evidence_snippet": string, "confidence": number 0 to 1, '
        '"suggested_fix": string}]}. '
        "Include exactly one finding object per requirement listed below, using the exact rule_id."
    )
    context_lines = [f"Jurisdiction: {pack.jurisdiction_name}", f"Product category: {pack.product_category}"]
    if context.imported is not None:
        context_lines.append(f"Imported product: {context.imported}")
    if context.single_ingredient is not None:
        context_lines.append(f"Single ingredient product: {context.single_ingredient}")
    if context.notes:
        context_lines.append(f"Notes: {context.notes}")

    user_text = (
        "\n".join(context_lines)
        + "\n\nRequirements:\n"
        + _rules_context(pack)
        + "\n\nOCR extracted text from the label image:\n"
        + (ocr_text or "(no text extracted)")
    )
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        },
    ]


def _evidence(snippet: str) -> list[Evidence]:
    snippet = (snippet or "").strip()
    if not snippet:
        return []
    kind = "absence" if snippet.lower().startswith(("no ", "not found", "missing", "absent")) else "ocr_text"
    return [Evidence(kind=kind, locator="baseline_single_prompt", snippet=snippet[:300])]


def _finding_for_rule(rule: Rule, raw: dict | None, source_lookup: dict[str, tuple[str, str]]) -> Finding:
    source_name, source_url = source_lookup.get(rule.source_id, ("", ""))
    if raw is None:
        return Finding(
            finding_id=f"{rule.rule_id}-baseline",
            rule_id=rule.rule_id,
            rule_reference=rule.source_reference,
            requirement=rule.requirement,
            status=Status.needs_review,
            severity=rule.severity,
            explanation="The baseline model did not return a verdict for this requirement.",
            evidence=[],
            confidence=0.0,
            suggested_fix=rule.suggested_fix,
            source_name=source_name,
            source_url=source_url,
        )

    status_raw = str(raw.get("status", "")).upper()
    status = Status(status_raw) if status_raw in _STATUS_VALUES else Status.needs_review
    confidence = raw.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5

    return Finding(
        finding_id=f"{rule.rule_id}-baseline",
        rule_id=rule.rule_id,
        rule_reference=rule.source_reference,
        requirement=rule.requirement,
        status=status,
        severity=rule.severity,
        explanation=str(raw.get("explanation", "")).strip() or "No explanation provided.",
        evidence=_evidence(str(raw.get("evidence_snippet", ""))),
        confidence=confidence,
        suggested_fix=str(raw.get("suggested_fix", "")).strip() or rule.suggested_fix,
        source_name=source_name,
        source_url=source_url,
    )


def run_baseline(
    image_bytes: bytes,
    context: ProductContext,
    case_id: str | None = None,
    mime_type: str = "image/png",
) -> tuple[ComplianceReport, TraceRecorder]:
    start = time.monotonic()
    trace = TraceRecorder(system="baseline", case_id=case_id)

    pack = rules.load_rule_pack(context.jurisdiction)
    trace.log("baseline", "load_rule_pack", result=f"{len(pack.rules)} rules loaded", tool_used="rules.load_rule_pack")

    raw_text = ocr.extract_text(image_bytes)
    trace.log(
        "baseline",
        "ocr_extract",
        tool_used="pytesseract",
        result=f"{len(raw_text)} characters extracted",
    )

    if settings.mock_mode:
        parsed, usage = _mock_response(pack)
        trace.log(
            "baseline",
            "single_llm_call",
            tool_used="mock",
            result=f"{len(parsed['findings'])} mock findings returned",
            decision="LABELGUARD_MODE=mock, no live model call made",
        )
    else:
        image_data_url = llm_client.image_to_data_url(image_bytes, mime_type)
        messages = _build_messages(pack, raw_text, context, image_data_url)
        parsed, usage = llm_client.chat_json(messages)
        trace.log(
            "baseline",
            "single_llm_call",
            tool_used=f"llm:{context.jurisdiction.value}",
            result=f"{len(parsed.get('findings', []))} findings returned",
            decision="single prompt produced full report, no separate verification",
        )

    by_rule_id = {str(f.get("rule_id")): f for f in parsed.get("findings", []) if isinstance(f, dict)}
    findings = [_finding_for_rule(r, by_rule_id.get(r.rule_id), rules.source_lookup(pack)) for r in pack.rules]

    product_name = parsed.get("product_name")
    runtime = time.monotonic() - start
    compliance_report = report.build_report(
        findings,
        pack,
        product_name,
        system="baseline",
        runtime_seconds=runtime,
        token_usage=usage,
    )
    trace.log("baseline", "report_generated", result=compliance_report.overall_status, duration_ms=int(runtime * 1000))
    trace.save()
    return compliance_report, trace
