# Decisions and assumptions

Recorded as they are made. Each entry states the assumption and why it was necessary.

## M1-01 Two jurisdictions: India and the UK

Both publish current, freely readable, official guidance that states mandatory label
particulars plainly. India gives precise regulation numbers in the FSSAI compendium
PDF, the UK gives plain language duties on GOV.UK. They also differ in interesting
ways, which gives the evaluation a genuine cross jurisdiction case: India requires a
separate "Contains" allergen statement, a veg or non-veg mark and an FSSAI licence
number, while the UK requires allergen emphasis inside the ingredients list and a UK
food business operator address.

## M1-02 Rule text is quoted, not paraphrased from memory

Every rule carries `source_excerpt` copied from the cited document, plus
`source_reference` and `source_url`. The India excerpts come from the FSSAI compendium
Version-I dated 23.09.2021. The UK excerpts come from GOV.UK and Food Standards Agency
business guidance pages retrieved on 2026-08-31. Where an article number of assimilated
Regulation (EU) No 1169/2011 could not be verified directly (legislation.gov.uk did not
return readable content), the rule cites the government guidance page that states the
duty rather than inventing an article number.

## M1-03 Physical size rules are conditional

Character height in mm (India regulation 6(3)) and x-height in mm (UK guidance) cannot
be derived from an image without knowing the physical pack size. These rules are
evaluated only when pack dimensions are supplied, which for evaluation cases comes from
`label_spec.pack` (px_per_cm plus panel area) and in the UI comes from optional user
input. Otherwise the finding is NEEDS_REVIEW, never FAIL.

## M1-04 Synthetic labels rendered from a spec

Cases store a `label_spec` rather than a checked in image. The renderer produces the
same PNG on any machine, so the evaluation is reproducible from a clean clone, and a
case variant (missing field, blur, rotation, small font) is a small edit to data rather
than image editing.

## M1-05 No working model credential in this environment

The shell provides `OPENAI_BASE_URL=https://aipipe.org/openai/v1` but `OPENAI_API_KEY`
is the placeholder string `NEW_KEY`. The project therefore reads its own
`LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` from `.env`, and ships
`LABELGUARD_MODE=mock` with recorded fixtures so that the demo, the tests and the full
pipeline run without a credential. Measured metrics require a real key and are labelled
with the model used. A real key must be supplied by the developer before Milestone 2
can produce live baseline numbers.

## M1-06 Gemini as default provider, reached through its OpenAI-compatible endpoint

The developer raised training a custom model on Kaggle and hosting it on Hugging Face
instead of calling a hosted LLM. Rejected: the hackathon brief explicitly excludes
custom model training (`labelguard_prompt.md` sections 17, 18, 26), a same-day
fine-tuned model would not match a strong hosted vision model on OCR-style extraction,
and it adds a non-reproducible training step plus separate hosting infra that judges
would need to re-run from a clean clone. The developer has Gemini API credits, and
`OPENAI_API_KEY` in this shell is only a placeholder, so Gemini becomes the default
provider. Gemini exposes an OpenAI-compatible endpoint
(`https://generativelanguage.googleapis.com/v1beta/openai/`), so the backend keeps a
single `openai`-SDK-shaped client rather than adding a second SDK, and the provider,
base URL, model names and key all come from `.env` so swapping to any other
OpenAI-compatible provider, including the aipipe.org proxy already present in this
shell, is a configuration change, not a rewrite.

## M2-01 Any FAIL forces overall FAIL, regardless of severity

`backend/app/services/report.py` sets `overall_status = FAIL` whenever any requirement
FAILs, not only when a critical one does. A low severity FAIL still means a real
requirement was not met, and softening the headline verdict for it would undercut the
evidence-first, no-false-reassurance principle in section 7 of the brief. Severity still
drives ordering and the critical failure count shown separately in the summary.

## M2-02 Presentation rules default to NEEDS_REVIEW, not PASS, as the expected status

RULE-IN-FOOD-012 and RULE-UK-FOOD-011 (character height and x-height) cannot be verified
from an image without a real physical measurement pipeline, which is out of scope per
M1-03. The first draft of the IN-001 and UK-001 annotations set `expected_overall` to
PASS while still marking these two rules NEEDS_REVIEW, which is self-contradictory given
M2-01: any NEEDS_REVIEW makes the overall status NEEDS_REVIEW. Fixed by making
NEEDS_REVIEW the primary expected status for both rules in every case, with PASS as an
accepted alternative, and correcting `expected_overall` on the two compliant cases to
NEEDS_REVIEW. This is also the philosophically consistent choice: a system that admits
it cannot verify a physical measurement from a photo should be rewarded for saying so,
not pushed toward a confident PASS it cannot actually support.

## M2-03 Evidence grounding metric treats vision_observation evidence as unverifiable, not ungrounded

`evaluation/evaluate.py` checks whether a finding's evidence snippet is a literal
substring of the OCR text. The first baseline run showed this unfairly penalising
genuinely visual claims, for example "green square symbol with a green circle inside"
for the veg mark, which can never appear in OCR text by definition. Evidence tagged
`vision_observation` is now counted as grounded automatically rather than requiring a
text match. The baseline itself still tags this kind of evidence as plain `ocr_text`
rather than `vision_observation`, since its single prompt does not distinguish evidence
modality, so its measured grounding rate (0.352 on the Milestone 2 run) is a real,
lower number, not an artifact of the metric. See IMPROVEMENT_CHANGELOG.md.

## M2-04 Baseline gets rule text and applicability conditions, but not pack dimensions

The baseline prompt in `backend/app/agents/baseline_agent.py` includes the full rule
pack (id, requirement, severity, applicability summary and conditions, source
reference) and the image and OCR text, matching the brief's requirement that baseline
and agent receive the same rule information. It does not receive
`ProductContext.pack_largest_surface_cm2` or `principal_panel_area_cm2`, even though
`evaluation/evaluate.py` now wires those through from each case. A genuinely naive
single-prompt baseline would not think to ask for or use pack dimensions either, so
leaving them out keeps the baseline a fair "reasonable naive implementation" per
section 8, rather than quietly giving it a capability a naive implementation would not
have. The Milestone 3 agent is free to use them in its compliance step.
