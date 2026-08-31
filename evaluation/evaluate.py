from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.schemas import ComplianceReport, Jurisdiction, ProductContext  # noqa: E402
from app.services import ocr as ocr_service  # noqa: E402
from app.services.scoring import precision_recall_f1, score_case  # noqa: E402

CASES_DIR = ROOT / "evaluation" / "cases"
ANNOTATIONS_DIR = ROOT / "evaluation" / "annotations"
RESULTS_DIR = ROOT / "evaluation" / "results"


def load_cases() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(CASES_DIR.glob("*.json"))]


def load_annotation(case_id: str) -> dict:
    return json.loads((ANNOTATIONS_DIR / f"{case_id}.json").read_text())


def run_system(system: str, case: dict) -> tuple[ComplianceReport, float]:
    image_path = ROOT / case["image"]
    if not image_path.exists():
        raise FileNotFoundError(
            f"{image_path} does not exist, run scripts/render_labels.py first"
        )
    image_bytes = image_path.read_bytes()
    pack_spec = case.get("label_spec", {}).get("pack", {})
    context = ProductContext(
        jurisdiction=Jurisdiction(case["jurisdiction"]),
        imported=case.get("context", {}).get("imported"),
        single_ingredient=case.get("context", {}).get("single_ingredient"),
        pack_largest_surface_cm2=pack_spec.get("largest_surface_area_cm2"),
        principal_panel_area_cm2=pack_spec.get("principal_panel_area_cm2"),
    )

    start = time.monotonic()
    if system == "baseline":
        from app.agents.baseline_agent import run_baseline

        result, _trace = run_baseline(image_bytes, context, case_id=case["case_id"])
    elif system == "agent":
        from app.agents.pipeline import run_agent

        result, _trace = run_agent(image_bytes, context, case_id=case["case_id"])
    else:
        raise ValueError(f"unknown system {system}")
    runtime = time.monotonic() - start
    return result, runtime


def print_comparison() -> int:
    baseline_path = RESULTS_DIR / "baseline_latest.json"
    agent_path = RESULTS_DIR / "agent_latest.json"
    if not baseline_path.exists() or not agent_path.exists():
        print("Need both evaluation/results/baseline_latest.json and agent_latest.json.")
        print("Run --system baseline and --system agent first.")
        return 1

    baseline = json.loads(baseline_path.read_text())
    agent = json.loads(agent_path.read_text())

    if baseline["case_count"] != agent["case_count"]:
        print(
            f"WARNING: baseline ran {baseline['case_count']} cases, agent ran "
            f"{agent['case_count']}. This comparison is not apples to apples."
        )

    rows = [
        ("cases evaluated", baseline["case_count"], agent["case_count"]),
        ("requirement-level F1", baseline["requirement_level_f1"]["f1"], agent["requirement_level_f1"]["f1"]),
        ("precision", baseline["requirement_level_f1"]["precision"], agent["requirement_level_f1"]["precision"]),
        ("recall", baseline["requirement_level_f1"]["recall"], agent["requirement_level_f1"]["recall"]),
        ("flagged F1", baseline["flagged_f1"]["f1"], agent["flagged_f1"]["f1"]),
        ("status accuracy", baseline["status_accuracy"], agent["status_accuracy"]),
        ("applicability accuracy", baseline["applicability_accuracy"], agent["applicability_accuracy"]),
        ("overall status accuracy", baseline["overall_status_accuracy"], agent["overall_status_accuracy"]),
        ("evidence grounding rate", baseline["evidence_grounding_rate"], agent["evidence_grounding_rate"]),
        ("avg runtime per case (s)", baseline["runtime_seconds_avg"], agent["runtime_seconds_avg"]),
        ("total tokens", baseline["token_usage_total"], agent["token_usage_total"]),
    ]

    print("\n=== Baseline vs Agent ===")
    print(f"baseline: {baseline['generated_at']}")
    print(f"agent:    {agent['generated_at']}")
    print()
    header = f"{'metric':<26}{'baseline':>12}{'agent':>12}{'delta':>12}"
    print(header)
    print("-" * len(header))
    for name, b_val, a_val in rows:
        delta = ""
        if isinstance(b_val, (int, float)) and isinstance(a_val, (int, float)) and name not in ("cases evaluated",):
            delta = f"{a_val - b_val:+.3f}" if isinstance(a_val, float) else f"{a_val - b_val:+d}"
        print(f"{name:<26}{b_val!s:>12}{a_val!s:>12}{delta:>12}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["baseline", "agent"])
    parser.add_argument("--cases", nargs="*", help="restrict to these case ids")
    parser.add_argument("--compare", action="store_true", help="print baseline vs agent from the latest results")
    args = parser.parse_args()

    if args.compare:
        return print_comparison()
    if not args.system:
        print("Pass --system baseline|agent, or --compare to read the latest results.")
        return 1

    cases = load_cases()
    if args.cases:
        cases = [c for c in cases if c["case_id"] in args.cases]
    if not cases:
        print("no cases matched")
        return 1

    case_results = []
    total_tp = total_fp = total_fn = 0
    total_flagged_tp = total_flagged_fp = total_flagged_fn = 0
    total_status_matches = total_status_total = 0
    total_app_correct = total_app_total = 0
    total_evidence_grounded = total_evidence = 0
    total_runtime = 0.0
    total_tokens = 0
    failures = []

    for case in cases:
        case_id = case["case_id"]
        annotation = load_annotation(case_id)
        print(f"running {args.system} on {case_id} ...")
        try:
            report, runtime = run_system(args.system, case)
        except Exception as exc:
            print(f"  FAILED: {exc}")
            failures.append({"case_id": case_id, "error": str(exc)})
            continue

        raw_text = ocr_service.extract_text((ROOT / case["image"]).read_bytes())
        scores = score_case(report, annotation, raw_text)
        overall_match = report.overall_status == annotation["expected_overall"]

        total_evidence_grounded += scores["evidence_grounded"]
        total_evidence += scores["evidence_total"]
        total_tp += scores["tp"]
        total_fp += scores["fp"]
        total_fn += scores["fn"]
        total_flagged_tp += scores["flagged_tp"]
        total_flagged_fp += scores["flagged_fp"]
        total_flagged_fn += scores["flagged_fn"]
        total_status_matches += scores["status_matches"]
        total_status_total += scores["status_total"]
        total_app_correct += scores["applicability_correct"]
        total_app_total += scores["applicability_total"]
        total_runtime += runtime
        total_tokens += report.token_usage.get("total_tokens", 0)

        case_results.append(
            {
                "case_id": case_id,
                "expected_overall": annotation["expected_overall"],
                "actual_overall": report.overall_status,
                "overall_match": overall_match,
                "runtime_seconds": round(runtime, 2),
                "token_usage": report.token_usage,
                "scores": scores,
            }
        )
        precision, recall, f1 = precision_recall_f1(scores["tp"], scores["fp"], scores["fn"])
        print(
            f"  overall {report.overall_status} (expected {annotation['expected_overall']}) "
            f"| tp={scores['tp']} fp={scores['fp']} fn={scores['fn']} | f1={f1} | {runtime:.1f}s"
        )

    precision, recall, f1 = precision_recall_f1(total_tp, total_fp, total_fn)
    flagged_precision, flagged_recall, flagged_f1 = precision_recall_f1(
        total_flagged_tp, total_flagged_fp, total_flagged_fn
    )
    status_accuracy = round(total_status_matches / total_status_total, 3) if total_status_total else 0.0
    applicability_accuracy = (
        round(total_app_correct / total_app_total, 3) if total_app_total else 0.0
    )
    overall_accuracy = (
        round(sum(1 for c in case_results if c["overall_match"]) / len(case_results), 3)
        if case_results
        else 0.0
    )
    evidence_grounding_rate = (
        round(total_evidence_grounded / total_evidence, 3) if total_evidence else 0.0
    )

    summary = {
        "system": args.system,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(case_results),
        "failures": failures,
        "requirement_level_f1": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
        },
        "flagged_f1": {
            "precision": flagged_precision,
            "recall": flagged_recall,
            "f1": flagged_f1,
        },
        "status_accuracy": status_accuracy,
        "applicability_accuracy": applicability_accuracy,
        "overall_status_accuracy": overall_accuracy,
        "evidence_grounding_rate": evidence_grounding_rate,
        "runtime_seconds_total": round(total_runtime, 2),
        "runtime_seconds_avg": round(total_runtime / len(case_results), 2) if case_results else 0.0,
        "token_usage_total": total_tokens,
        "case_results": case_results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"{args.system}_{stamp}.json"
    out_path.write_text(json.dumps(summary, indent=2))
    latest_path = RESULTS_DIR / f"{args.system}_latest.json"
    latest_path.write_text(json.dumps(summary, indent=2))

    print("\n=== Summary ===")
    print(f"system: {args.system}")
    print(f"cases: {len(case_results)} ({len(failures)} failed to run)")
    print(f"requirement-level detection F1: precision={precision} recall={recall} f1={f1}")
    print(
        f"flagged F1 (FAIL+NEEDS_REVIEW): precision={flagged_precision} recall={flagged_recall} f1={flagged_f1}"
    )
    print(f"status accuracy: {status_accuracy}")
    print(f"applicability accuracy: {applicability_accuracy}")
    print(f"overall status accuracy: {overall_accuracy}")
    print(f"evidence grounding rate: {evidence_grounding_rate}")
    print(f"avg runtime per case: {summary['runtime_seconds_avg']}s")
    print(f"total tokens: {total_tokens}")
    try:
        display_path = out_path.relative_to(ROOT)
    except ValueError:
        display_path = out_path
    print(f"results written to {display_path}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
