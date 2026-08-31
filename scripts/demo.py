from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.baseline_agent import run_baseline  # noqa: E402
from app.agents.pipeline import run_agent  # noqa: E402
from app.config import settings  # noqa: E402
from app.models.schemas import Jurisdiction, ProductContext  # noqa: E402

DEMO_CASE_ID = "UK-003"
DEMO_IMAGE = ROOT / "evaluation" / "images" / f"{DEMO_CASE_ID}.png"


def _rule_line(finding) -> str:
    return f"  [{finding.status.value:13}] {finding.rule_id}  {finding.requirement[:68]}"


def _print_header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    if not DEMO_IMAGE.exists():
        print(f"Demo image missing: {DEMO_IMAGE}")
        print("Run this first: ./.venv/bin/python scripts/render_labels.py")
        return 1

    print("LabelGuard demo")
    print("A label with one real, deliberate violation and no others.")
    if settings.mock_mode:
        print("Mode: MOCK -- LABELGUARD_MODE=mock, no live model calls, deterministic stub output.")
        print("      Set LABELGUARD_MODE=live and a real LLM_API_KEY in .env to see real reasoning.")
    else:
        print(f"Mode: LIVE -- calling {settings.llm_model}")
    print(f"Case: {DEMO_CASE_ID} (Golden Oat Granola), jurisdiction United Kingdom, packaged food")
    print(f"Image: {DEMO_IMAGE.relative_to(ROOT)}")
    print(
        "The label has a decorative front-panel brand name but no full food business "
        "operator name and address anywhere on the pack. Everything else is compliant."
    )

    image_bytes = DEMO_IMAGE.read_bytes()
    context = ProductContext(jurisdiction=Jurisdiction.uk, imported=False, single_ingredient=False)

    _print_header("STEP 1: BASELINE -- OCR + one LLM call, no retrieval, no verification")
    start = time.monotonic()
    baseline_report, _baseline_trace = run_baseline(image_bytes, context, case_id=None)
    print(f"Ran in {time.monotonic() - start:.1f}s, {baseline_report.token_usage.get('total_tokens', 0)} tokens")
    print(f"Overall: {baseline_report.overall_status}")
    print("Findings that are not a plain PASS:")
    for f in baseline_report.findings:
        if f.status.value != "PASS":
            print(_rule_line(f))

    _print_header("STEP 2: AGENT -- extraction, retrieval, compliance, verification")
    start = time.monotonic()
    agent_report, agent_trace = run_agent(image_bytes, context, case_id=None)
    print(f"Ran in {time.monotonic() - start:.1f}s, {agent_report.token_usage.get('total_tokens', 0)} tokens")
    print("Agent trace:")
    for e in agent_trace.trace.events:
        print(f"  - {e.step}: {e.result}")
    print(f"Overall: {agent_report.overall_status}")
    print("Findings that are not a plain PASS:")
    for f in agent_report.findings:
        if f.status.value != "PASS":
            print(_rule_line(f))
            if f.evidence:
                print(f"      evidence: {f.evidence[0].snippet[:80]!r}")

    _print_header("WHAT DIFFERED BETWEEN THE TWO SYSTEMS")
    baseline_fails = {f.rule_id for f in baseline_report.findings if f.status.value == "FAIL"}
    agent_fails = {f.rule_id for f in agent_report.findings if f.status.value == "FAIL"}
    only_baseline = sorted(baseline_fails - agent_fails)
    only_agent = sorted(agent_fails - baseline_fails)
    if only_baseline:
        print(f"Baseline-only FAILs (candidate false positives): {only_baseline}")
    if only_agent:
        print(f"Agent-only FAILs: {only_agent}")
    if not only_baseline and not only_agent:
        print("Both systems agreed on every FAIL finding for this specific case.")
    print(
        "\nSee evaluation/results/*_latest.json and IMPROVEMENT_CHANGELOG.md for the "
        "full 15-case comparison this single example is drawn from."
    )

    _print_header("NEXT STEPS")
    print("Full evaluation, both systems:")
    print("  ./.venv/bin/python evaluation/evaluate.py --system baseline")
    print("  ./.venv/bin/python evaluation/evaluate.py --system agent")
    print("  ./.venv/bin/python evaluation/evaluate.py --compare")
    print("Web UI:")
    print("  LABELGUARD_MODE=mock ./.venv/bin/python -m uvicorn app.main:app --app-dir backend --port 8000")
    print("  npm --prefix frontend run dev")
    print("Tests:")
    print("  ./.venv/bin/python -m pytest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
