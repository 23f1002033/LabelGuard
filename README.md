# LabelGuard

AI-powered global product label compliance auditing with evidence-backed verification.

Upload a packaged food label, pick a target market, and get a requirement by
requirement compliance report where every finding carries evidence, a rule reference,
a confidence value and a suggested fix.

LabelGuard is a compliance assistant. It does not give legal advice and it never
asserts that a product is legally compliant.

## Status

Milestone 1 of 5 complete: inspection, scope, rule packs, schemas and scaffolding.
The application code arrives in Milestones 2 and 3. Commands marked "(Milestone N)"
do not exist yet.

## Scope

- Product type: pre-packaged food for retail sale
- Markets: India (FSSAI Labelling and Display Regulations, 2020) and Great Britain
  (Food Information Regulations 2014 and assimilated Regulation (EU) No 1169/2011,
  as stated in current GOV.UK and Food Standards Agency guidance)
- 13 India requirements and 12 UK requirements, listed with sources in
  `rules/india/food_label_rules.json` and `rules/uk/food_label_rules.json`

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
- `LABELGUARD_MODE=mock` uses recorded fixtures, runs offline and is deterministic.
  Used for the demo and the test suite. (Milestone 2)

## Commands

Available now:

```
./.venv/bin/python scripts/validate_schemas.py
```

Validates both rule packs against `rules/rule_pack.schema.json`, validates every
evaluation case and annotation, checks that annotations only reference rule ids that
exist, and checks that no data file contains non-ASCII characters.

Expected output:

```
OK: 2 rule packs, 1 cases, 1 annotations
```

Arriving later:

```
./.venv/bin/python scripts/render_labels.py                       (Milestone 2)
./.venv/bin/python evaluation/evaluate.py --system baseline       (Milestone 2)
./.venv/bin/python evaluation/evaluate.py --system agent          (Milestone 3)
./.venv/bin/python evaluation/evaluate.py --compare               (Milestone 4)
./.venv/bin/python scripts/demo.py                                (Milestone 3)
./.venv/bin/python -m uvicorn app.main:app --app-dir backend      (Milestone 3)
npm --prefix frontend run dev                                     (Milestone 3)
./.venv/bin/python -m pytest                                      (Milestone 2)
```

## Layout

```
backend/app/models/schemas.py   agent interfaces and report data structures
backend/app/config.py           environment configuration
rules/                          jurisdiction rule packs and their JSON schema
evaluation/cases/               inputs, including the label spec each image renders from
evaluation/annotations/         expected findings, never shown to the systems under test
docs/architecture.md            scope, pipeline, agent roles, risks
docs/evaluation.md              metric definitions and how numbers are produced
docs/decisions.md               assumptions made and why
scripts/validate_schemas.py     data integrity check
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
