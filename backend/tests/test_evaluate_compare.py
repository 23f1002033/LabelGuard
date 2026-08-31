import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "evaluation" / "evaluate.py"

_spec = importlib.util.spec_from_file_location("evaluate", SPEC_PATH)
evaluate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evaluate)


def _write_result(path, case_count, f1):
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-01-01T00:00:00Z",
                "case_count": case_count,
                "requirement_level_f1": {"precision": f1, "recall": f1, "f1": f1},
                "flagged_f1": {"precision": f1, "recall": f1, "f1": f1},
                "status_accuracy": f1,
                "applicability_accuracy": f1,
                "overall_status_accuracy": f1,
                "evidence_grounding_rate": f1,
                "runtime_seconds_avg": 10.0,
                "token_usage_total": 100,
            }
        )
    )


def test_compare_missing_results_returns_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(evaluate, "RESULTS_DIR", tmp_path)
    code = evaluate.print_comparison()
    assert code == 1
    assert "Run --system baseline" in capsys.readouterr().out


def test_compare_prints_delta_when_both_present(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(evaluate, "RESULTS_DIR", tmp_path)
    _write_result(tmp_path / "baseline_latest.json", 15, 0.8)
    _write_result(tmp_path / "agent_latest.json", 15, 0.9)
    code = evaluate.print_comparison()
    out = capsys.readouterr().out
    assert code == 0
    assert "requirement-level F1" in out
    assert "+0.100" in out


def test_compare_warns_on_mismatched_case_counts(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(evaluate, "RESULTS_DIR", tmp_path)
    _write_result(tmp_path / "baseline_latest.json", 7, 0.8)
    _write_result(tmp_path / "agent_latest.json", 15, 0.9)
    evaluate.print_comparison()
    out = capsys.readouterr().out
    assert "WARNING" in out
