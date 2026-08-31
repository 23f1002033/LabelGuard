# LabelGuard

AI-powered global product label compliance auditing with evidence-backed verification.

Upload a packaged food label, pick a target market, and get a requirement by
requirement compliance report where every finding carries evidence, a rule reference,
a confidence value and a suggested fix.

LabelGuard is a compliance assistant. It does not give legal advice and it never
asserts that a product is legally compliant.

## Status

Milestone 2 of 5 complete: baseline system, deterministic label renderer, first 7
evaluation cases, and the first real baseline metrics. The verification-oriented
agent pipeline and the web UI arrive in Milestone 3. Commands marked "(Milestone N)"
do not exist yet.

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
- Node 20 or newer (developed on 24.7.0), needed from Milestone 3
- tesseract, for OCR: `brew install tesseract` on macOS,
  `sudo apt-get install tesseract-ocr` on Debian or Ubuntu

## Install

```
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` and set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` for your
provider. Any OpenAI compatible endpoint works. No key is committed and none is
required to run in mock mode.

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

See `IMPROVEMENT_CHANGELOG.md` for what these numbers mean and the two concrete
failure patterns already observed (applicability confusion on conditional rules, and
run-to-run instability on one allergen case).

```
./.venv/bin/python -m pytest
```

Runs the backend test suite (27 tests as of Milestone 2): rule pack integrity, report
status and scoring logic, baseline agent plumbing in mock mode, and label renderer
determinism. No API key needed, all tests run offline.

Arriving later:

```
./.venv/bin/python evaluation/evaluate.py --system agent          (Milestone 3)
./.venv/bin/python evaluation/evaluate.py --compare                (Milestone 4)
./.venv/bin/python scripts/demo.py                                 (Milestone 3)
./.venv/bin/python -m uvicorn app.main:app --app-dir backend       (Milestone 3)
npm --prefix frontend run dev                                      (Milestone 3)
```

## Layout

```
backend/app/models/schemas.py     agent interfaces and report data structures
backend/app/config.py             environment configuration
backend/app/agents/baseline_agent.py  single-call baseline system
backend/app/services/            OCR, LLM client, rule loading, scoring, report building, tracing
backend/tests/                   pytest suite, all offline
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
