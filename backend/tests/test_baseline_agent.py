from pathlib import Path

import pytest
from app.agents.baseline_agent import run_baseline
from app.config import settings
from app.models.schemas import Jurisdiction, ProductContext, Status

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_IMAGE = ROOT / "evaluation" / "images" / "IN-001.png"


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "labelguard_mode", "mock")


def test_baseline_runs_in_mock_mode_without_network():
    if not SAMPLE_IMAGE.exists():
        pytest.skip("run scripts/render_labels.py first to generate evaluation images")
    context = ProductContext(jurisdiction=Jurisdiction.india)
    compliance_report, trace = run_baseline(SAMPLE_IMAGE.read_bytes(), context, case_id=None)

    assert compliance_report.system == "baseline"
    assert len(compliance_report.findings) == 14
    assert all(f.status == Status.needs_review for f in compliance_report.findings)
    assert compliance_report.token_usage["total_tokens"] == 0
    assert any(e.step == "single_llm_call" for e in trace.trace.events)


def test_baseline_covers_every_rule_even_when_model_says_nothing():
    if not SAMPLE_IMAGE.exists():
        pytest.skip("run scripts/render_labels.py first to generate evaluation images")
    context = ProductContext(jurisdiction=Jurisdiction.uk)
    compliance_report, _trace = run_baseline(SAMPLE_IMAGE.read_bytes(), context, case_id=None)
    assert len(compliance_report.findings) == 12
