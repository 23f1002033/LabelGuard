from __future__ import annotations

from app.config import settings
from app.models.schemas import CandidateFinding, Evidence, LabelFacts, Rule, SelectedRule, Status
from app.services import llm_client

_STATUS_VALUES = {s.value for s in Status}
_PHYSICAL_MEASUREMENT_FACT = "min_text_height_mm"


def _facts_context(facts: LabelFacts, required_facts: list[str]) -> str:
    lines = []
    for name in required_facts:
        field = facts.get(name)
        if field is None:
            lines.append(f"- {name}: not extracted")
            continue
        evidence = field.evidence[0].snippet if field.evidence else ""
        confidence_label = "confidence it is genuinely absent" if not field.present else "confidence"
        lines.append(
            f"- {name}: present={field.present}, value={field.value!r}, "
            f"{confidence_label}={field.confidence:.2f}, evidence={evidence!r}"
        )
    return "\n".join(lines) if lines else "(no specific facts required)"


def _build_messages(facts: LabelFacts, rules_to_judge: list[SelectedRule]) -> list[dict]:
    system_prompt = (
        "You are a compliance analyst reviewing a food label. You are given "
        "structured facts already extracted from the label, each with a "
        "confidence and evidence snippet, and a list of requirements that a "
        "separate retrieval step has already determined apply to this product. "
        "For each requirement, decide PASS if the facts show it is satisfied, "
        "FAIL if the facts show it is genuinely not satisfied, or NEEDS_REVIEW if "
        "the facts are ambiguous, low confidence, or you cannot tell either way. "
        "Do not decide applicability, that decision has already been made; judge "
        "only whether the requirement is met given the facts you were given. "
        "The requirement text is the full legal wording. Some requirements come "
        "with an MVP scope note stating exactly what this automated system checks; "
        "when a note is given, judge strictly against that note and the facts, not "
        "against parts of the legal text the note says are out of scope. When a "
        "rule has no note, judge against the full requirement text and the facts. "
        "If you are genuinely unsure whether the facts satisfy a requirement, "
        "prefer NEEDS_REVIEW over FAIL; only mark FAIL when the facts clearly show "
        "the requirement is not met. "
        "Never cite evidence that was not given to you, and never claim a fact "
        "is present if its present flag is false. "
        "Respond with a JSON object: {\"findings\": ["
        '{"rule_id": string, "status": "PASS|FAIL|NEEDS_REVIEW", "explanation": '
        'string, "evidence_snippet": string, "confidence": number 0 to 1, '
        '"suggested_fix": string}]}. Include exactly one finding per requirement listed.'
    )
    blocks = []
    for sr in rules_to_judge:
        rule = sr.rule
        block = f"{rule.rule_id} [{rule.severity.value}] {rule.requirement}\n"
        if rule.notes:
            block += f"MVP scope note: {rule.notes}\n"
        block += f"Facts:\n{_facts_context(facts, rule.required_facts)}"
        blocks.append(block)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n\n".join(blocks)},
    ]


def _evidence(snippet: str) -> list[Evidence]:
    snippet = (snippet or "").strip()
    if not snippet:
        return []
    kind = "absence" if snippet.lower().startswith(("no ", "not found", "missing", "absent")) else "fact"
    return [Evidence(kind=kind, locator="compliance_agent", snippet=snippet[:300])]


def _not_applicable_finding(rule: Rule, reason: str) -> CandidateFinding:
    return CandidateFinding(
        finding_id=f"{rule.rule_id}-agent",
        rule_id=rule.rule_id,
        status=Status.not_applicable,
        severity=rule.severity,
        explanation=reason,
        evidence=[],
        confidence=0.95,
        suggested_fix="",
    )


def _physical_measurement_finding(rule: Rule) -> CandidateFinding:
    return CandidateFinding(
        finding_id=f"{rule.rule_id}-agent",
        rule_id=rule.rule_id,
        status=Status.needs_review,
        severity=rule.severity,
        explanation=(
            "Physical text height in millimetres cannot be measured from a photo "
            "without a calibrated physical reference. This MVP does not implement "
            "pixel-to-millimetre measurement, so this requirement needs review "
            "against a physical sample."
        ),
        evidence=[],
        confidence=0.3,
        suggested_fix=rule.suggested_fix,
    )


def _finding_from_raw(rule: Rule, raw: dict | None) -> CandidateFinding:
    if raw is None:
        return CandidateFinding(
            finding_id=f"{rule.rule_id}-agent",
            rule_id=rule.rule_id,
            status=Status.needs_review,
            severity=rule.severity,
            explanation="The compliance model did not return a verdict for this requirement.",
            evidence=[],
            confidence=0.0,
            suggested_fix=rule.suggested_fix,
        )
    status_raw = str(raw.get("status", "")).upper()
    status = (
        Status(status_raw)
        if status_raw in _STATUS_VALUES and status_raw != "NOT_APPLICABLE"
        else Status.needs_review
    )
    confidence = raw.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5
    return CandidateFinding(
        finding_id=f"{rule.rule_id}-agent",
        rule_id=rule.rule_id,
        status=status,
        severity=rule.severity,
        explanation=str(raw.get("explanation", "")).strip() or "No explanation provided.",
        evidence=_evidence(str(raw.get("evidence_snippet", ""))),
        confidence=confidence,
        suggested_fix=str(raw.get("suggested_fix", "")).strip() or rule.suggested_fix,
    )


def _mock_findings(rules_to_judge: list[SelectedRule]) -> dict:
    return {
        "findings": [
            {
                "rule_id": sr.rule.rule_id,
                "status": "NEEDS_REVIEW",
                "explanation": "LABELGUARD_MODE=mock, no live model call was made.",
                "evidence_snippet": "",
                "confidence": 0.0,
                "suggested_fix": sr.rule.suggested_fix,
            }
            for sr in rules_to_judge
        ]
    }


def run_compliance(facts: LabelFacts, selected_rules: list[SelectedRule]) -> tuple[list[CandidateFinding], dict]:
    findings: list[CandidateFinding] = []
    to_judge: list[SelectedRule] = []

    for sr in selected_rules:
        if not sr.applicable:
            findings.append(_not_applicable_finding(sr.rule, sr.applicability_reason))
        elif _PHYSICAL_MEASUREMENT_FACT in sr.rule.required_facts:
            findings.append(_physical_measurement_finding(sr.rule))
        else:
            to_judge.append(sr)

    if not to_judge:
        return findings, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    if settings.mock_mode:
        parsed = _mock_findings(to_judge)
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    else:
        messages = _build_messages(facts, to_judge)
        parsed, usage = llm_client.chat_json(messages)

    by_rule_id = {str(f.get("rule_id")): f for f in parsed.get("findings", []) if isinstance(f, dict)}
    for sr in to_judge:
        findings.append(_finding_from_raw(sr.rule, by_rule_id.get(sr.rule.rule_id)))

    return findings, usage
