import importlib.util
import json
import sys
from pathlib import Path

import pytest
from app.config import settings

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "evaluation" / "evaluate.py"

_spec = importlib.util.spec_from_file_location("evaluate", SPEC_PATH)
evaluate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evaluate)


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "labelguard_mode", "mock")


def test_evaluate_main_runs_baseline_end_to_end(tmp_path, monkeypatch):
    if not (ROOT / "evaluation" / "images" / "IN-001.png").exists():
        pytest.skip("run scripts/render_labels.py first to generate evaluation images")

    monkeypatch.setattr(evaluate, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", ["evaluate.py", "--system", "baseline", "--cases", "IN-001"])

    exit_code = evaluate.main()

    assert exit_code == 0
    latest = tmp_path / "baseline_latest.json"
    assert latest.exists()
    result = json.loads(latest.read_text())
    assert result["case_count"] == 1
    assert result["failures"] == []
    assert result["system"] == "baseline"


def test_evaluate_main_runs_agent_end_to_end(tmp_path, monkeypatch):
    if not (ROOT / "evaluation" / "images" / "IN-001.png").exists():
        pytest.skip("run scripts/render_labels.py first to generate evaluation images")

    monkeypatch.setattr(evaluate, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", ["evaluate.py", "--system", "agent", "--cases", "IN-001"])

    exit_code = evaluate.main()

    assert exit_code == 0
    result = json.loads((tmp_path / "agent_latest.json").read_text())
    assert result["case_count"] == 1
    assert result["system"] == "agent"


def test_evaluate_main_rejects_unknown_case_id(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["evaluate.py", "--system", "baseline", "--cases", "NOT-A-REAL-CASE"])
    exit_code = evaluate.main()
    assert exit_code == 1
    assert "no cases matched" in capsys.readouterr().out


def test_evaluate_main_requires_system_or_compare(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["evaluate.py"])
    exit_code = evaluate.main()
    assert exit_code == 1
    assert "--system" in capsys.readouterr().out
