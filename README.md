# LabelGuard

AI-powered global product label compliance auditing with evidence-backed verification.

Upload a packaged food label, pick a target market, and get a requirement by
requirement compliance report where every finding carries evidence, a rule reference,
a confidence value and a suggested fix.

LabelGuard is a compliance assistant. It does not give legal advice and it never
asserts that a product is legally compliant.

## Status

All 5 milestones complete. Submission-ready. 15 evaluation cases, a confirmed
baseline-vs-agent comparison, a documented largest failure mode with a real
before/after fix, 84 offline tests, a runnable demo, committed agent trajectory
traces, and a failure analysis with a hot take grounded in this project's own run
history. See `docs/failure_analysis.md` for the last of those, and
`IMPROVEMENT_CHANGELOG.md` for the complete, dated history of every real change and
the numbers that justified it.

## Scope

- Product type: pre-packaged food for retail sale
- Markets: India (FSSAI Labelling and Display Regulations, 2020) and Great Britain
  (Food Information Regulations 2014 and assimilated Regulation (EU) No 1169/2011,
  as stated in current GOV.UK and Food Standards Agency guidance)
- 14 India requirements and 12 UK requirements, listed with sources in
  `rules/india/food_label_rules.json` and `rules/uk/food_label_rules.json`
- 15 synthetic evaluation cases (9 India, 6 UK), rendered deterministically from
  `evaluation/cases/*.json`, covering: a compliant reference per jurisdiction, isolated
  single violations across every rule category, a multi-violation case, two
  warning-trigger cases, an explicit matched cross-jurisdiction pair (identical label
  content, opposite jurisdiction, genuinely different correct answer), a genuinely
  ambiguous fact case, a false-positive trap grounded in an actual regulatory nuance
  (coconut is not a regulated tree nut), and a fully compliant but rotated/blurred/noisy
  robustness case

This is a bounded subset of each country's labelling law, not full coverage. See
`docs/architecture.md` section 3 for what is deliberately excluded.

## Prerequisites

- Python 3.11 or newer (developed on 3.14.0)
- Node 20 or newer (developed on 24.7.0), needed to run the frontend
- tesseract, for OCR: `brew install tesseract` on macOS,
  `sudo apt-get install tesseract-ocr` on Debian or Ubuntu

## Install

```
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
npm --prefix frontend install
```

Then edit `.env` and set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` for your
provider. The default is Gemini through its OpenAI-compatible endpoint (get a key at
aistudio.google.com/apikey); any OpenAI-compatible endpoint works. No key is committed
and none is required to run in mock mode.

## Modes

- `LABELGUARD_MODE=live` calls the configured model. Required for measured metrics.
- `LABELGUARD_MODE=mock` skips the model call and returns a fixed NEEDS_REVIEW stub
  for every rule, using zero tokens. Runs offline, deterministic, used by the test
  suite so `pytest` needs no API key. Not a source of accuracy numbers.

## Commands

Fastest way to see it work end to end:

```
./.venv/bin/python scripts/render_labels.py
./.venv/bin/python scripts/demo.py
```

Runs the baseline and the agent side by side on the same real case (UK-003, a
missing-business-address violation) and prints both systems' findings and traces so
you can see where they agree and where they differ. Uses `LABELGUARD_MODE` and
`LLM_API_KEY` from `.env`; without a live key it explains this and runs in mock mode
instead. Takes about 1 minute in live mode, under 5 seconds in mock mode.

```
./.venv/bin/python scripts/validate_schemas.py
```

Validates both rule packs against `rules/rule_pack.schema.json`, validates every
evaluation case and annotation, checks that annotations only reference rule ids that
exist, and checks that no data file contains non-ASCII characters.

Expected output:

```
OK: 2 rule packs, 15 cases, 15 annotations
```

```
./.venv/bin/python scripts/render_labels.py
```

Renders every case in `evaluation/cases/*.json` into `evaluation/images/*.png` from
its `label_spec`. Rendering is deterministic (a fixed bundled font, a seed derived
from the case id), so the same case produces byte-identical output on any machine.
Pass `--case IN-001` to render just one case.

```
./.venv/bin/python evaluation/evaluate.py --system baseline
```

Runs the baseline system (OCR plus one LLM call) over every case with an annotation,
scores it against `evaluation/annotations/`, prints a summary, and writes full detail
to `evaluation/results/baseline_<timestamp>.json` and `baseline_latest.json`. Pass
`--cases IN-001 IN-002` to restrict to specific cases. Requires images to already be
rendered and, in live mode, requires `LLM_API_KEY` to be set in `.env`.

Actual output from the full 15-case set on 2026-08-31, model gemini-2.5-flash:

```
requirement-level detection F1: precision=0.727 recall=0.941 f1=0.821
flagged F1 (FAIL+NEEDS_REVIEW): precision=0.684 recall=0.963 f1=0.8
status accuracy: 0.879
applicability accuracy: 0.872
overall status accuracy: 0.867
evidence grounding rate: 0.343
avg runtime per case: 23.57s
```

```
./.venv/bin/python evaluation/evaluate.py --system agent
```

Runs the full agent pipeline (extraction, retrieval, compliance, verification) over
the same cases and the same annotations as the baseline, so the comparison is apples
to apples.

Actual output from the full 15-case set on 2026-08-31, model gemini-2.5-flash:

```
requirement-level detection F1: precision=0.938 recall=0.882 f1=0.909
flagged F1 (FAIL+NEEDS_REVIEW): precision=0.968 recall=0.938 f1=0.952
status accuracy: 0.975
applicability accuracy: 1.0
overall status accuracy: 0.933
evidence grounding rate: 0.514
avg runtime per case: 32.93s
```

```
./.venv/bin/python evaluation/evaluate.py --compare
```

Reads `evaluation/results/baseline_latest.json` and `agent_latest.json` and prints a
metric-by-metric delta table. Warns instead of silently comparing if the two runs
covered different case counts.

Baseline vs agent on the same 15 cases: F1 0.821 to 0.909, precision 0.727 to 0.938
(the largest single gap of any run), applicability accuracy 0.872 to a perfect 1.0,
evidence grounding 0.343 to 0.514, at roughly 1.4x the runtime and 1.7x the tokens of
the baseline. This is the confirmed final Milestone 4 comparison, run after the
developer reset the Gemini API's monthly spending cap that had blocked an earlier
confirmation attempt. See `IMPROVEMENT_CHANGELOG.md` for the full story: two baseline
failure modes found in Milestone 2, three real bugs found and fixed while building the
agent in Milestone 3, and the largest failure mode plus its fix found and confirmed in
Milestone 4.

```
./.venv/bin/python -m pytest
```

Runs the backend test suite (84 tests): rule pack integrity, report and scoring logic,
every agent's plumbing and normalization edge cases in mock mode (extraction,
retrieval, compliance, verification, the full pipeline), evidence-kind mapping, the
FastAPI endpoints, a true end-to-end run of `evaluate.py` itself, the evaluation
comparison command, and label renderer determinism. No API key needed, all tests run
offline. Verified to also pass from a completely fresh `venv` outside this repo's
`.venv`, installing only from `requirements.txt`.

```
LABELGUARD_MODE=mock ./.venv/bin/python -m uvicorn app.main:app --app-dir backend --port 8000
```

Starts the backend API. `GET /api/health`, `GET /api/jurisdictions`, and
`POST /api/analyze` (multipart: `image`, `jurisdiction`, `system`, optional `imported`
and `single_ingredient`). Drop `LABELGUARD_MODE=mock` to use the live model.

```
npm --prefix frontend run dev
```

Starts the frontend on port 5173 (proxies `/api` to `http://127.0.0.1:8000`, see
`frontend/vite.config.js`). Upload a label, pick a jurisdiction, pick agent or
baseline, and get the same report structure the evaluation harness scores.

## Runtime and cost

Measured on the full 15-case set, model gemini-2.5-flash, 2026-08-31:

| | Baseline | Agent |
| --- | --- | --- |
| Avg time per case | 23.6s | 32.9s |
| Total tokens (15 cases) | 92,480 | 154,628 |
| Avg tokens per case | ~6,165 | ~10,309 |

These are real token counts from `evaluation/results/*_latest.json`, not estimates.
Dollar cost depends on your Gemini pricing tier and is not reproduced here since it
can change independently of this project; check current pricing at
ai.google.dev/pricing before running the full evaluation repeatedly. `scripts/demo.py`
(one case, both systems) takes about 1 minute total in live mode. The full test suite
and `scripts/validate_schemas.py` are both offline and take a few seconds.

## Layout

```
backend/app/models/schemas.py     agent interfaces and report data structures
backend/app/config.py             environment configuration
backend/app/main.py               FastAPI app
backend/app/api/analyze.py        POST /api/analyze: upload validation, runs baseline or agent
backend/app/api/meta.py           GET /api/health, GET /api/jurisdictions
backend/app/agents/baseline_agent.py    single-call baseline system
backend/app/agents/extraction_agent.py  vision + OCR to structured, evidence-tagged facts
backend/app/agents/retrieval_agent.py   deterministic applicability engine, no LLM call
backend/app/agents/compliance_agent.py  judges only the rules retrieval marked applicable
backend/app/agents/verification_agent.py  challenges candidate FAIL findings only
backend/app/agents/pipeline.py    orchestrates the four agents into one report
backend/app/services/            OCR, LLM client, rule loading, scoring, report building, tracing
backend/tests/                   pytest suite, all offline
frontend/                        Vite + React UI: upload, jurisdiction, analyze, report, agent trace
rules/                           jurisdiction rule packs and their JSON schema
evaluation/cases/                inputs, including the label spec each image renders from
evaluation/annotations/          expected findings, never shown to the systems under test
evaluation/evaluate.py           evaluation harness, scoring, metrics, results
evaluation/results/              metric output per run, latest.json plus timestamped history
evaluation/traces/               per-case agent trajectory logs
scripts/validate_schemas.py      data integrity check
scripts/render_labels.py         deterministic synthetic label renderer
scripts/demo.py                  baseline vs agent, side by side, on one real case
docs/architecture.md             scope, pipeline, agent roles, risks
docs/evaluation.md               metric definitions and how numbers are produced
docs/decisions.md                assumptions made and why
docs/agent_traces.md             trace file format, worked examples, how to regenerate
docs/failure_analysis.md         the actual biggest failure mode found, and the hot take
```

## Data handling

Uploaded images are held in memory or in a temporary directory for the duration of a
request and are not stored permanently. Uploads are restricted by MIME type and size
through `ALLOWED_UPLOAD_TYPES` and `UPLOAD_MAX_BYTES`. Traces record workflow events,
rule ids and decisions only. No API keys, no personal data and no model reasoning
traces are logged.

## Disclaimer

LabelGuard produces an AI-assisted preliminary compliance review. It is not legal
advice, it does not replace review by a qualified professional or a regulator, and its
rule packs cover only the subset of requirements listed in this repository.
