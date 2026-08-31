# Agent trajectory traces

Every run of either system, whether from `evaluation/evaluate.py`, `scripts/demo.py`,
or the API, produces a structured trace: one JSON object per case per system, one event
per pipeline step, written to `evaluation/traces/<system>_<case_id>.json`. This is the
"representative agent trajectory" record for the project. There are 30 committed trace
files as of Milestone 5 (15 baseline, 15 agent, one pair per evaluation case), each from
the last live evaluation run.

## What is logged

Each event, defined by `TraceEvent` in `backend/app/models/schemas.py` and written by
`backend/app/services/trace.py`, carries:

- `timestamp`
- `agent`: which component ran (`extraction_agent`, `retrieval_agent`,
  `compliance_agent`, `verification_agent`, `baseline`, or `pipeline` for
  orchestration-level events)
- `step`: a short machine name, e.g. `extract_label_fields`
- `tool_used`: what actually ran (`pytesseract`, `llm`, `deterministic_applicability_engine`)
- `result`: a one-line, human-readable summary
- `decision`: present only when there is a structured, safe-to-show decision to record,
  for example the retrieval agent's derived `ApplicabilitySignals`
- `duration_ms`: present on the final step, the whole pipeline's wall-clock time

## What is deliberately never logged

Per section 23/24 of the project brief: no API keys, no raw model chain-of-thought, no
full prompts or full model responses, no personal data. `result` and `decision` are
short structured summaries the code itself constructs, not anything copied verbatim
from a model's internal reasoning. This is also what the frontend's trace panel
displays directly (`frontend/src/App.jsx`, `TraceTimeline`), so the same privacy bar
applies to what a user sees live and to what is written to disk.

## Baseline trace shape (4 events)

```
load_rule_pack -> ocr_extract -> single_llm_call -> report_generated
```

Example, `evaluation/traces/baseline_UK-003.json` (verbatim):

```json
{
  "case_id": "UK-003",
  "system": "baseline",
  "events": [
    {"step": "load_rule_pack", "tool_used": "rules.load_rule_pack", "result": "12 rules loaded"},
    {"step": "ocr_extract", "tool_used": "pytesseract", "result": "422 characters extracted"},
    {"step": "single_llm_call", "tool_used": "llm:UK", "result": "12 findings returned",
     "decision": "single prompt produced full report, no separate verification"},
    {"step": "report_generated", "result": "FAIL", "duration_ms": 17531}
  ]
}
```

## Agent trace shape (6 events)

```
load_rule_pack -> extract_label_fields -> select_applicable_rules ->
generate_candidate_findings -> verify_findings -> generate_final_report
```

Example, `evaluation/traces/agent_IN-004.json` (verbatim, the multi-violation case):

```json
{
  "case_id": "IN-004",
  "system": "agent",
  "events": [
    {"step": "load_rule_pack", "result": "14 rules loaded"},
    {"step": "extract_label_fields", "tool_used": "pytesseract + vision_model",
     "result": "Extracted label fields: 12/22 fields present"},
    {"step": "select_applicable_rules", "tool_used": "deterministic_applicability_engine",
     "result": "Selected applicable rules: 11/14 rules apply",
     "decision": "signals: {'single_ingredient_food': False, 'imported_product': False, 'contains_listed_allergen': True, ...}"},
    {"step": "generate_candidate_findings", "tool_used": "llm",
     "result": "Generated candidate findings: 14 findings, 3 candidate FAIL"},
    {"step": "verify_findings", "tool_used": "llm",
     "result": "Verified findings: 3 FAIL findings challenged, 0 rejected"},
    {"step": "generate_final_report", "result": "FAIL", "duration_ms": 34517}
  ]
}
```

Note the `select_applicable_rules` step's `decision` field: it shows the exact derived
signals (`contains_listed_allergen: True`, and so on) that decided which of the 14
rules were even in play, before any LLM call happened. This is what "purposeful use of
context" looks like in a trace: an inspectable, deterministic decision, not a black box.

## How to produce a fresh set

```
./.venv/bin/python evaluation/evaluate.py --system baseline
./.venv/bin/python evaluation/evaluate.py --system agent
```

Each overwrites `evaluation/traces/<system>_<case_id>.json` for every case run. For a
single, narrated, human-readable walkthrough instead of raw JSON, run
`./.venv/bin/python scripts/demo.py`, which prints both systems' traces for one case
side by side.
