from pathlib import Path

import pytest
from app.agents.pipeline import run_agent
from app.config import settings
from app.models.schemas import Jurisdiction, ProductContext

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_IMAGE = ROOT / "evaluation" / "images" / "IN-001.png"


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "labelguard_mode", "mock")


def test_pipeline_runs_end_to_end_in_mock_mode():
    if not SAMPLE_IMAGE.exists():
        pytest.skip("run scripts/render_labels.py first to generate evaluation images")
    context = ProductContext(jurisdiction=Jurisdiction.india)
    compliance_report, trace = run_agent(SAMPLE_IMAGE.read_bytes(), context, case_id=None)

    assert compliance_report.system == "agent"
    assert len(compliance_report.findings) == 14
    steps = [e.step for e in trace.trace.events]
    assert steps == [
        "load_rule_pack",
        "extract_label_fields",
        "select_applicable_rules",
        "generate_candidate_findings",
        "verify_findings",
        "generate_final_report",
    ]


def test_pipeline_covers_every_rule_for_uk_pack_too():
    if not SAMPLE_IMAGE.exists():
        pytest.skip("run scripts/render_labels.py first to generate evaluation images")
    context = ProductContext(jurisdiction=Jurisdiction.uk)
    compliance_report, _trace = run_agent(SAMPLE_IMAGE.read_bytes(), context, case_id=None)
    assert len(compliance_report.findings) == 12
