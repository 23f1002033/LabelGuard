# LabelGuard architecture and Milestone 1 plan

## 1. What this is

LabelGuard checks a packaged food label image against the mandatory labelling
requirements of a target market, and returns an evidence backed compliance report.
It is a compliance assistant. It never asserts legal compliance, and every finding
carries evidence, a rule reference and a confidence value.

## 2. Repository state at the start

The directory contained only `labelguard_prompt.md`. There was no existing stack,
dependency file or code, so nothing had to be preserved or migrated.

Environment checked on 2026-08-31:

- Python 3.14.0 (Homebrew), venv and pip work
- Node 24.7.0, npm 11.5.1
- tesseract binary present at /opt/homebrew/bin/tesseract
- `OPENAI_BASE_URL` points at https://aipipe.org/openai/v1 (an OpenAI compatible proxy)
- `OPENAI_API_KEY` in the shell is the literal placeholder value `NEW_KEY`, so there
  is no working model credential yet. The developer has Gemini API credits instead, so
  the default provider was changed to Gemini's OpenAI-compatible endpoint, see
  `docs/decisions.md` M1-06
- fastapi, uvicorn, pydantic, pillow, pytesseract, openai and pytest all install
  cleanly on Python 3.14

## 3. MVP scope

Product type: pre-packaged food sold at retail.

Jurisdictions: India and the United Kingdom (Great Britain).

The scope is a bounded subset, not a claim of full legal coverage:

- India: 13 requirements from the Food Safety and Standards (Labelling and Display)
  Regulations, 2020, covering name of food, ingredients, nutrition, veg or non-veg
  mark, brand owner name and address, FSSAI logo and licence, net quantity, batch or
  lot, date marking, country of origin for imports, allergen Contains statement,
  minimum character height, and Schedule II warning statements.
- UK: 12 requirements from current GOV.UK and Food Standards Agency guidance on the
  Food Information Regulations 2014 and assimilated Regulation (EU) No 1169/2011,
  covering name of the food, ingredients, allergen emphasis, net quantity, date
  marking, food business operator name and UK address, storage and use instructions,
  lot marking, country of origin, nutrition declaration, x-height, and prescribed
  warnings.

Every rule stores its source name, URL, reference and a verbatim excerpt. Nothing in
the rule packs was written from memory. Requirements that cannot be judged reliably
from an image, such as physical font height, are marked
`needs_professional_review` and are expected to resolve to NEEDS_REVIEW rather than
FAIL unless pack dimensions are supplied.

Out of scope for the MVP: cosmetics and other product classes, prepacked for direct
sale rules, Northern Ireland specifics, category specific compositional standards,
full Legal Metrology placement rules, nutrient value verification, and claims
substantiation.

## 4. Pipeline

```
label image + jurisdiction + product context
        |
        v
  Extraction agent        OCR (tesseract) + vision model, per field confidence
        |
        v
  LabelFacts (structured, evidence tagged)
        |
        v
  Retrieval agent         load jurisdiction rule pack, derive applicability
        |                 signals, return only applicable rules
        v
  Compliance agent        one judgement per rule, PASS / FAIL / NEEDS_REVIEW /
        |                 NOT_APPLICABLE with evidence and suggested fix
        v
  Verification agent      challenges FAIL and low confidence findings against
        |                 the raw OCR text and the rule applicability, may reject
        v
  Report generator        ordered, evidence backed report plus trace
```

The baseline system is a separate implementation: OCR plus one LLM call that
receives the same image, the same rule pack and asks for the same report structure.
No separate extraction, no applicability derivation, no verification.

## 5. Agent responsibilities and interfaces

All interfaces are defined in `backend/app/models/schemas.py`.

| Agent | Input | Output | Purpose that no other agent has |
| --- | --- | --- | --- |
| Extraction | image bytes, ProductContext | LabelFacts | Turn pixels into named fields with evidence and confidence, and say "absent" honestly |
| Retrieval | jurisdiction, category, LabelFacts | list[SelectedRule] + ApplicabilitySignals | Decide which requirements are even in play, so the analyst never argues about rules that do not apply |
| Compliance | LabelFacts, SelectedRule list | list[CandidateFinding] | Judge one requirement at a time against facts, not against the raw image |
| Verification | CandidateFinding, LabelFacts, raw OCR text, Rule | VerificationResult | Attack the finding: is the evidence really absent, does the rule really apply, is the confidence justified |
| Report | verified findings, rule sources | ComplianceReport | Ordering, scoring, sources, disclaimer |

Statuses are PASS, FAIL, NEEDS_REVIEW and NOT_APPLICABLE. A verifier verdict of
`rejected` demotes a FAIL to NEEDS_REVIEW or PASS with a recorded reason. It never
promotes a finding to FAIL on its own.

Implemented as of Milestone 3:
`backend/app/agents/extraction_agent.py`, `retrieval_agent.py`, `compliance_agent.py`,
`verification_agent.py`, orchestrated by `pipeline.py`. One deviation from the table
above: the retrieval agent makes no LLM call at all, it is deterministic Python
matching `ApplicabilitySignals` (derived from facts and product context) against each
rule's `applicability.conditions`. See docs/decisions.md M3-04 for why. The
verification agent, in the implementation, only receives and only ever runs on
candidate findings with status FAIL, not on every finding, to keep the check targeted
and the token cost bounded; see docs/decisions.md M3-03.

## 6. Data structures

- `ExtractedField`: present, value, confidence, evidence list, extractor
- `LabelFacts`: raw_text plus a dict of the 25 fact names in `FACT_NAMES`
- `ApplicabilitySignals`: the derived flags that rule conditions reference, such as
  `imported_product`, `contains_listed_allergen`, `schedule_two_trigger`
- `Rule` / `RulePack`: as defined by `rules/rule_pack.schema.json`
- `CandidateFinding`, `VerificationResult`, `Finding`, `ComplianceReport`
- `TraceEvent` and `AnalysisTrace` for the demo trace panel and the trace files

The rule field `required_facts` uses the same vocabulary as `FACT_NAMES`, and
`applicability.conditions[].fact` uses the `ApplicabilitySignals` vocabulary. Both
links are checked by `scripts/validate_schemas.py`, so a rule pack cannot silently
reference a fact the pipeline does not produce.

## 7. Rule pack design

```
rules/
  rule_pack.schema.json
  india/food_label_rules.json
  uk/food_label_rules.json
```

Adding a jurisdiction means adding one directory with one JSON file that validates
against the schema, plus applicability signals if the new rules need a flag that does
not exist yet. No agent code changes.

## 8. Evaluation design

Cases are synthetic and rendered deterministically from a `label_spec` in the case
file, so the same PNG is produced on any machine. Expected findings live in a
separate `evaluation/annotations/` file so that no system can read the answers from
its own input.

Target: 12 to 15 cases across both jurisdictions, including a clean compliant label,
single missing field cases, multiple violation cases, a cross jurisdiction case where
the same label passes in one market and fails in the other, a low legibility case,
and at least two false positive traps.

Primary metric: requirement level detection F1, where a detection is a
(case_id, rule_id) pair the system reports as FAIL and the annotation also marks
FAIL. This directly measures "did we find the real problems without inventing any".

Secondary metrics: precision, recall, false positive rate on compliant requirements,
flagged F1 counting FAIL and NEEDS_REVIEW together, status accuracy across all four
statuses, evidence grounding rate (fraction of findings whose quoted evidence is
actually present in the OCR text or is a justified absence claim), applicability
accuracy on NOT_APPLICABLE rules, runtime and token usage.

Full definitions live in `docs/evaluation.md`.

## 9. One day feasibility

Realistic for one day, in milestone order: baseline plus label renderer plus first
metrics; then the four agents, the FastAPI backend and a small React frontend; then
the full case set, the baseline versus agent comparison and one real iteration; then
tests, README, changelog, traces and failure analysis.

Deliberately excluded: vector database, agent framework, docker, auth, persistence,
model training, live regulation crawling at request time.

## 10. Known risks

1. Resolved in Milestone 2: a working Gemini key is now in `.env` and verified against
   both the text and vision endpoints. `LABELGUARD_MODE=mock` still exists as a zero
   token, offline fallback for the test suite (`backend/app/agents/baseline_agent.py`),
   not for measured metrics.
2. OCR quality on synthetic labels is good, which can flatter the extraction stage
   relative to real photographs. The renderer supports rotation, blur and noise
   through the `pack` block of the label spec, but none of the 7 Milestone 2 cases use
   them yet; harder variants are planned for the Milestone 4 case set expansion.
3. The baseline is already observed to be non-deterministic at temperature 0: the same
   case, same model, back-to-back runs, produced a different FAIL/PASS verdict on one
   requirement. See IMPROVEMENT_CHANGELOG.md "Baseline observation 2". This affects how
   much weight any single evaluation run can bear, agent and baseline alike.
4. Physical size rules (mm and x-height) are not measurable from an image alone.
   Mitigation: pack dimensions are now wired from the case's `label_spec.pack` into
   `ProductContext` in `evaluation/evaluate.py`, but neither the baseline prompt nor a
   dedicated agent step actually uses them yet to compute a real mm measurement, so
   these two rules are annotated NEEDS_REVIEW as the primary expected status in every
   case, not FAIL or PASS, and both baseline and future agent are expected to land
   there rather than overclaim.
5. Synthetic labels are not real product photographs, so absolute numbers are not a
   claim about field performance. The comparison between baseline and agent is fair
   because both see identical inputs.
