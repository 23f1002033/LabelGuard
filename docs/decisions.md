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

## M3-01 Do not cap extraction confidence for absent facts

`backend/app/agents/extraction_agent.py` originally clamped confidence to at most 0.3
whenever a field's `present` flag was false, on the reasoning that the model should
not sound too sure about something it did not find. In practice this destroyed exactly
the signal the evidence-first design in section 7 of the brief depends on: a model that
is genuinely certain a required declaration is absent (confidence 1.0 in the raw API
response) got relabelled as barely-confident, which then made the compliance agent
treat a clear violation as merely uncertain. Removed the clamp; confidence now means
"how sure the extractor is that this field's present/value reading is correct," in
both directions, and a confident absence is allowed to read as confident. See
IMPROVEMENT_CHANGELOG.md "Agent v1 bug 1".

## M3-02 Compliance judgment scope follows rule.notes, not the full legal text

The compliance agent is given the full `requirement` legal text plus only the
`required_facts` an MVP actually extracts. Several rules' legal text names details
(colour contrast, physical grouping of two dates, true manufacturing weight order)
that are not separately extracted, and the model was correctly declining to confidently
PASS things it had no evidence for. The tempting fix, telling the model to PASS anyway
when facts are missing, was rejected: it would make the system assert things it cannot
actually verify, directly contradicting section 7's "never allow unsupported claims."
The correct fix was already half-built: the rule pack's `notes` field exists
specifically to document MVP scope narrowing (see M1's rule schema), it just was not
being read by the compliance agent. Wired `rule.notes` into the compliance prompt and
added notes to the affected rules (RULE-IN-FOOD-002/006/009, RULE-UK-FOOD-002/005/006)
stating exactly what this system checks for each. This keeps every PASS honestly
scoped to what was actually verified, rather than either overclaiming or drowning in
NEEDS_REVIEW. See IMPROVEMENT_CHANGELOG.md "Agent v1 bug 2".

## M3-03 Verification agent only challenges FAIL findings

`backend/app/agents/verification_agent.py` runs only on candidate findings with status
FAIL, and can only move a finding to NEEDS_REVIEW or PASS, never to FAIL. This matches
section 6.D's own worked example (the verifier checks and may reject an analyst's
"missing" claim, it does not go looking for new violations) and keeps the token cost
bounded to the requirements that are actually being flagged as problems, which is also
where being wrong is most costly to a user acting on the report. A verifier that could
also promote NEEDS_REVIEW or PASS to FAIL would let it invent new violations the
compliance agent never found, which is a different and riskier job than the one
section 6.D describes.

## M3-04 Retrieval agent is deterministic Python, not an LLM call

`backend/app/agents/retrieval_agent.py` derives `ApplicabilitySignals` from extracted
facts and product context using keyword matching and simple boolean logic, then
matches each rule's `applicability.conditions` against those signals directly in code.
No LLM call. This was a deliberate choice, not a shortcut: applicability decisions
should be auditable and reproducible given the same facts, and Baseline observation 1
showed exactly what goes wrong when applicability judgment is left to open-ended LLM
reasoning mixed in with compliance judgment. The tradeoff is that the signal-derivation
heuristics (allergen keyword lists, date-marking exemption keywords, warning trigger
keywords) are only as good as the keyword lists in the file, and will not catch a
phrasing they do not recognise; this is an explicit, inspectable limitation rather than
a silent one.

## M4-01 RULE-IN-FOOD-010 split into origin and importer-address rules

`RULE-IN-FOOD-010` originally bundled two distinct FSSAI provisions under one rule id:
country of origin (regulation 5(12)(a)) and importer name/address (regulation 5(6)(b)).
Its `requirement` text and `source_excerpt` only ever described the origin duty, but
`required_facts` also listed `importer_name_address`. The compliance agent, correctly
following the M3-02 pattern of judging against the stated requirement text, reasonably
ignored the importer fact it was never asked about, so an imported label missing an
Indian importer address could pass this rule on origin declaration alone. Verified live
on IN-007 (a UK-formatted label evaluated under India rules with no Indian importer
address) before fixing: extraction correctly found the importer address absent, but the
rule passed anyway. Split into `RULE-IN-FOOD-010` (origin only, required_facts =
[country_of_origin]) and new `RULE-IN-FOOD-014` (importer address only, required_facts
= [importer_name_address], citing FSSAI 5(6)(b), quote checked against the original
extracted regulation text from `docs/architecture.md`'s Milestone 1 source). All 9
India annotations updated to add the corresponding RULE-IN-FOOD-014 expectation.

## M4-02 Rule notes must never claim something is checked when required_facts doesn't supply it

`RULE-IN-FOOD-007`'s notes field said "retail sale price and consumer care details are
checked as presence," but `required_facts` only ever supplied `net_quantity`. This is
the same failure class as M3-02 (compliance agent hedges when asked to judge something
it has no evidence for) but caused by the notes field itself lying about what facts the
system actually has, rather than the notes field being absent. It recurred on 5 of 15
cases, the single largest failure pattern found in the Milestone 4 case set, because
every case that reaches this always-applicable rule triggers it. Rewrote the notes to
state plainly that retail sale price and consumer care are not evaluated "in either
direction," and audited every other rule's notes against its required_facts for the
same contradiction; none found. General principle going forward: a rule's notes field
must only describe what its own `required_facts` actually let the compliance agent see,
never what the rule pack author wishes it also covered.

## M4-03 Cross-jurisdiction cases reuse existing label content rather than new renders

IN-007 and UK-005 reuse UK-001's and IN-001's exact `label_spec` respectively, just
under the other jurisdiction with a different `context.imported` value. This was
deliberate: the pedagogical point is that identical label content gets a genuinely
different correct answer depending on jurisdiction, which is only a clean demonstration
if the content is literally identical, not merely similar. The alternative (designing
two new, thematically similar but not identical labels) would have left open the
question of whether any observed difference came from the jurisdiction or from
incidental differences in the label content.

## M4-04 Gemini monthly spend cap blocked final confirmation, fixes kept anyway (resolved)

The API key hit `RESOURCE_EXHAUSTED` (monthly spending cap, confirmed with a second
minimal call immediately after, same error) partway through a final confirmation run,
after the RULE-IN-FOOD-007 notes fix (M4-02) had been made but before it could be
re-verified at full 15-case scale, and after a second, smaller notes fix to
RULE-UK-FOOD-007 had been made and verified only on the single case that surfaced it
(UK-004). Rather than revert the fixes to match only what could be re-confirmed, or
fabricate a plausible-looking final run, both fixes were kept because: the reasoning
for each is sound and independently checkable against the rule pack and the FSSAI/UK
source text; RULE-IN-FOOD-007's fix follows the exact pattern already validated at
scale for six other rules in Milestone 3 (M3-02); and RULE-UK-FOOD-007's fix was
live-verified on the case that found it, just not re-confirmed at full-set scale.

Resolved: the developer reset the spend cap. Before spending more on a full run, both
individually-uncertain fixes were re-checked in isolation first (cheap, fast) to rule
out a persistent bug before attributing anything to noise: RULE-UK-FOOD-007 on UK-004
and RULE-UK-FOOD-006 on UK-005 (a new mismatch that had appeared in the interim
confirmation attempt) both returned their expected status on a clean re-check,
consistent with temperature-0 sampling noise rather than a real defect. Only then was
the full baseline vs agent comparison re-run to completion; see IMPROVEMENT_CHANGELOG.md
"M4 confirmed after quota reset" for the final numbers.
