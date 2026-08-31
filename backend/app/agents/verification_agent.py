from __future__ import annotations

from app.config import settings
from app.models.schemas import CandidateFinding, LabelFacts, Rule, Status, Verdict, VerificationResult
from app.services import llm_client

_VERDICT_VALUES = {v.value for v in Verdict}
_ALLOWED_REVISED = {Status.passed.value, Status.needs_review.value}


def _facts_summary(facts: LabelFacts, required_facts: list[str]) -> str:
    lines = []
    for name in required_facts:
        field = facts.get(name)
        if field is None:
            lines.append(f"  - {name}: not extracted")
            continue
        lines.append(f"  - {name}: present={field.present}, value={field.value!r}")
    return "\n".join(lines) if lines else "  (no specific facts required)"


def _build_messages(facts: LabelFacts, items: list[tuple[CandidateFinding, Rule]]) -> list[dict]:
    system_prompt = (
        "You are a verification reviewer checking FAIL findings from a compliance "
        "analyst before they are shown to a user. Do not redo the whole analysis. "
        "For each candidate FAIL finding, check whether the claim is actually "
        "supported: look at the extracted facts and the raw OCR text, and decide "
        "whether the evidence genuinely supports a FAIL, whether the rule really "
        "applies, and whether there is a contradiction, for example the OCR text "
        "actually contains the thing the analyst said was missing. "
        "Give a verdict for each finding: confirmed if the FAIL is well supported "
        "and should stand, rejected if the evidence does not actually support a "
        "FAIL and it should be downgraded, or uncertain if you cannot tell either "
        "way and it should be downgraded to a cautious review status. "
        "You may never upgrade anything to FAIL and you may only mark something "
        "confirmed if the missing or wrong evidence is genuinely absent from both "
        "the facts and the raw OCR text. "
        'Respond with a JSON object: {"verifications": ['
        '{"finding_id": string, "verdict": "confirmed|rejected|uncertain", '
        '"reason": string, "revised_status": "PASS or NEEDS_REVIEW or null, only '
        'set when verdict is rejected or uncertain"}]}.'
    )
    ocr_excerpt = (facts.raw_text or "")[:2000]
    blocks = [f"Raw OCR text from the label:\n{ocr_excerpt}"]
    for finding, rule in items:
        evidence_snippet = finding.evidence[0].snippet if finding.evidence else "(none cited)"
        blocks.append(
            f"Finding {finding.finding_id} for {rule.rule_id}: {rule.requirement}\n"
            f"Analyst explanation: {finding.explanation}\n"
            f"Analyst evidence: {evidence_snippet}\n"
            f"Analyst confidence: {finding.confidence:.2f}\n"
            f"Relevant facts:\n{_facts_summary(facts, rule.required_facts)}"
        )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n\n".join(blocks)},
    ]


def _result_from_raw(finding_id: str, raw: dict | None) -> VerificationResult:
    if raw is None:
        return VerificationResult(
            finding_id=finding_id,
            verdict=Verdict.uncertain,
            reason="The verification model did not return a verdict for this finding.",
            revised_status=Status.needs_review,
        )
    verdict_raw = str(raw.get("verdict", "")).lower()
    verdict = Verdict(verdict_raw) if verdict_raw in _VERDICT_VALUES else Verdict.uncertain

    revised_raw = raw.get("revised_status")
    revised_status = None
    if verdict in (Verdict.rejected, Verdict.uncertain):
        revised_str = str(revised_raw).upper() if revised_raw else ""
        revised_status = Status(revised_str) if revised_str in _ALLOWED_REVISED else Status.needs_review

    return VerificationResult(
        finding_id=finding_id,
        verdict=verdict,
        reason=str(raw.get("reason", "")).strip() or "No reason provided.",
        revised_status=revised_status,
    )


def _mock_results(items: list[tuple[CandidateFinding, Rule]]) -> dict:
    return {
        "verifications": [
            {
                "finding_id": finding.finding_id,
                "verdict": "uncertain",
                "reason": "LABELGUARD_MODE=mock, no live model call was made.",
                "revised_status": "NEEDS_REVIEW",
            }
            for finding, _rule in items
        ]
    }


def run_verification(
    facts: LabelFacts,
    candidate_findings: list[CandidateFinding],
    rules_by_id: dict[str, Rule],
) -> tuple[list[VerificationResult], dict]:
    items = [
        (finding, rules_by_id[finding.rule_id])
        for finding in candidate_findings
        if finding.status == Status.failed and finding.rule_id in rules_by_id
    ]

    if not items:
        return [], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    if settings.mock_mode:
        parsed = _mock_results(items)
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    else:
        messages = _build_messages(facts, items)
        parsed, usage = llm_client.chat_json(messages)

    by_finding_id = {
        str(v.get("finding_id")): v for v in parsed.get("verifications", []) if isinstance(v, dict)
    }
    results = [
        _result_from_raw(finding.finding_id, by_finding_id.get(finding.finding_id))
        for finding, _rule in items
    ]
    return results, usage
