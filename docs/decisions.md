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
