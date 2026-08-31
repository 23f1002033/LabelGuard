# LabelGuard

AI-powered global product label compliance auditing with evidence-backed verification.

Upload a packaged food label, pick a target market, and get a requirement by
requirement compliance report where every finding carries evidence, a rule reference,
a confidence value and a suggested fix.

LabelGuard is a compliance assistant. It does not give legal advice and it never
asserts that a product is legally compliant.

## Status

Milestone 3 of 5 complete: the four-agent pipeline (extraction, retrieval, compliance,
verification), a FastAPI backend, and a React frontend, wired together end to end from
upload to report. Expanding the case set to 10-15 with harder trap cases, and the
baseline-vs-agent comparison writeup, land in Milestone 4. Commands marked
"(Milestone N)" do not exist yet.

## Scope

- Product type: pre-packaged food for retail sale
- Markets: India (FSSAI Labelling and Display Regulations, 2020) and Great Britain
  (Food Information Regulations 2014 and assimilated Regulation (EU) No 1169/2011,
  as stated in current GOV.UK and Food Standards Agency guidance)
- 13 India requirements and 12 UK requirements, listed with sources in
  `rules/india/food_label_rules.json` and `rules/uk/food_label_rules.json`
- 7 synthetic evaluation cases so far (4 India, 3 UK), rendered deterministically from
  `evaluation/cases/*.json`; the full 10-15 case set with the harder trap cases
  (ambiguous label, low legibility, explicit cross-jurisdiction pair) lands in
  Milestone 4

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

```
./.venv/bin/python scripts/validate_schemas.py
```

Validates both rule packs against `rules/rule_pack.schema.json`, validates every
evaluation case and annotation, checks that annotations only reference rule ids that
exist, and checks that no data file contains non-ASCII characters.

Expected output:

```
OK: 2 rule packs, 7 cases, 7 annotations
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

Actual output from the 7-case set on 2026-08-31, model gemini-2.5-flash:

```
requirement-level detection F1: precision=0.75 recall=0.857 f1=0.8
flagged F1 (FAIL+NEEDS_REVIEW): precision=0.643 recall=0.9 f1=0.75
status accuracy: 0.875
applicability accuracy: 0.857
overall status accuracy: 0.714
evidence grounding rate: 0.352
avg runtime per case: 23.25s
```

```
./.venv/bin/python evaluation/evaluate.py --system agent
```

Runs the full agent pipeline (extraction, retrieval, compliance, verification) over
the same 7 cases and the same annotations as the baseline, so the comparison is
apples to apples.

Actual output from the 7-case set on 2026-08-31, model gemini-2.5-flash, confirmed
stable across two consecutive live runs:

```
requirement-level detection F1: precision=1.0 recall=1.0 f1=1.0
flagged F1 (FAIL+NEEDS_REVIEW): precision=0.867 recall=1.0 f1=0.929
status accuracy: 0.966
applicability accuracy: 1.0
overall status accuracy: 1.0
evidence grounding rate: 0.478
avg runtime per case: 32.4s
```

Baseline vs agent on the same 7 cases: F1 0.8 to 1.0, applicability accuracy 0.857 to
1.0, overall-status accuracy 0.714 to 1.0, evidence grounding 0.352 to 0.48, at roughly
1.4x the runtime and 1.8x the tokens of the baseline. See `IMPROVEMENT_CHANGELOG.md`
for the full story: two baseline failure modes found, three real bugs found and fixed
while building the agent, and what each fix actually changed.

```
./.venv/bin/python -m pytest
```

Runs the backend test suite (59 tests as of Milestone 3): rule pack integrity, report
and scoring logic, every agent's plumbing in mock mode (extraction, retrieval,
compliance, verification, the full pipeline), the FastAPI endpoints, and label
renderer determinism. No API key needed, all tests run offline.

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

Arriving later:

```
./.venv/bin/python evaluation/evaluate.py --compare    (Milestone 4)
./.venv/bin/python scripts/demo.py                      (Milestone 5)
```

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
docs/architecture.md             scope, pipeline, agent roles, risks
docs/evaluation.md               metric definitions and how numbers are produced
docs/decisions.md                assumptions made and why
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
