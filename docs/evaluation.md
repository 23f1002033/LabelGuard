# Evaluation design

## Inputs

- `evaluation/cases/<case_id>.json` holds the input: jurisdiction, product context and
  the `label_spec` used to render the image. Validated by `evaluation/case.schema.json`.
- `evaluation/annotations/<case_id>.json` holds the expected result. Validated by
  `evaluation/annotation.schema.json`. Systems under test never receive this file.
- Images are rendered from the label spec by `scripts/render_labels.py` (Milestone 2)
  into `evaluation/images/`. Rendering is deterministic, so images are reproducible
  and are not checked in as opaque binaries.

## Systems under test

- `baseline`: OCR text plus a single LLM call with the same rule pack, returning the
  same report structure.
- `agent`: extraction, retrieval, compliance, verification, report.

Both receive the same image, the same jurisdiction, the same product context and the
same rule pack, and are run with the same model and temperature.

## Primary metric

Requirement level detection F1.

A detection is a `(case_id, rule_id)` pair reported with status FAIL.

- true positive: annotation expects FAIL and the system reports FAIL
- false positive: system reports FAIL where the annotation expects PASS,
  NEEDS_REVIEW or NOT_APPLICABLE
- false negative: annotation expects FAIL and the system reports anything else

precision = tp / (tp + fp), recall = tp / (tp + fn), F1 = harmonic mean.

`accept_also` in an annotation widens the accepted set for a single requirement where
more than one status is defensible, for example a legibility rule that may reasonably
land on NEEDS_REVIEW. An accepted alternative counts as neither a false positive nor a
false negative.

## Secondary metrics

- flagged F1: FAIL and NEEDS_REVIEW both count as flagged. Rewards catching a problem
  even when the system is not certain.
- status accuracy: exact status match across all evaluated requirements.
- false positive rate: false positives divided by the number of requirements the
  annotation marks PASS or NOT_APPLICABLE.
- applicability accuracy: exact match on requirements annotated NOT_APPLICABLE.
- evidence grounding rate: fraction of reported findings, among those that cited any
  evidence, where the evidence is checkable and checks out: a snippet that literally
  appears in the OCR text, an explicit absence claim on a FAIL or NEEDS_REVIEW finding,
  or a claim tagged as a visual observation (evidence.kind = vision_observation), which
  cannot be substring-matched against OCR text by definition and is treated as
  unverifiable-by-this-metric rather than ungrounded. A system that tags genuinely
  visual claims (a symbol, a colour, a logo) as plain text evidence will score lower
  here than one that tags its evidence kind correctly, which is itself a meaningful
  signal about evidence discipline.
- coverage: fraction of applicable rules the system actually returned a status for.
- verifier rejection count and what it changed, agent system only.
- runtime per case and token usage per case.

## Running

```
python evaluation/evaluate.py --system baseline
python evaluation/evaluate.py --system agent
python evaluation/evaluate.py --compare
```

Results are written to `evaluation/results/<system>_<timestamp>.json` with per case
detail, and a summary table is printed. Traces are written to
`evaluation/traces/<system>_<case_id>.json`.

## Rules for honest numbers

- Metrics are only ever produced by running `evaluation/evaluate.py`. No number in any
  document is written by hand.
- Every reported comparison states the model, the mode, the case count and the date.
- Mock mode results are labelled as mock and are never presented as model performance.
