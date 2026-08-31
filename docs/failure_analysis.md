# Failure analysis and hot take

This is written after all four milestones of real evaluation, not before. Every
example below is a specific, dated, reproducible incident from this project's own
run history, not a hypothetical.

## The actual biggest failure mode: run-to-run non-determinism at temperature 0

The single most frequently recurring failure across the whole project was not a
design flaw in any one agent. It was the underlying LLM giving a different answer to
the same question, with the same input, at temperature 0, on different runs.

Observed instances, in order:

1. **Milestone 2.** `RULE-IN-FOOD-011` on case IN-003 (peanuts in the ingredients, no
   separate Contains statement): the baseline correctly returned FAIL on one run and
   incorrectly returned PASS on the very next run, same model, same case, no other
   change. Recorded as "Baseline observation 2" in `IMPROVEMENT_CHANGELOG.md`.
2. **Milestone 3.** Two consecutive full-set agent runs (`Agent v2`) produced
   different status accuracy (0.955 vs 0.966) and evidence grounding rate (0.44 vs
   0.48) on the identical 7 cases.
3. **Milestone 4, first pass.** The first full 15-case agent run showed a false
   negative on IN-003's allergen rule that a second run did not reproduce (see the
   IN-003 investigation in the Milestone 3 changelog rows, which recurred once more
   during the Milestone 4 case-set expansion before the extraction confidence fix was
   confirmed to hold).
4. **Milestone 4, quota-reset verification.** After the developer reset the Gemini
   spend cap, a fresh full run showed two *new* false positives that had not appeared
   in the prior confirmed run: `RULE-UK-FOOD-007` on UK-004 and `RULE-UK-FOOD-006` on
   UK-005. Both were re-checked in isolation and both returned their correct expected
   status on the very next call. Same rule pack, same case, same model, different
   answer.

Four independent incidents, spread across three milestones, on different rules, in
both jurisdictions, in both systems. This is not one bug to patch. It is a property
of the underlying model.

### Why the verification agent does not fully solve this

The verification agent (`backend/app/agents/verification_agent.py`) was built
specifically in response to incident 1, and it works exactly as designed: it only
ever runs on candidate FAIL findings, and it can only downgrade a FAIL to
NEEDS_REVIEW or PASS, never invent a new one. This measurably improved precision
across every Milestone 3 and 4 run (baseline precision 0.727-0.842 versus agent
precision 0.938-1.0 across the recorded runs).

But incidents 3 and 4 above were not FAIL findings gone wrong. They were the
compliance agent itself landing on a different status between runs, sometimes
PASS-to-FAIL, sometimes PASS-to-NEEDS_REVIEW. The verification agent, by design
(see `docs/decisions.md` M3-03), never even sees these, because it only inspects
candidates that are already FAIL. A finding that flips between PASS and
NEEDS_REVIEW, or that is a FAIL on one run and would have been correctly confirmed
FAIL had the verifier seen it but happened to come back PASS this time, is
completely outside what the current architecture checks.

In other words: separating extraction, retrieval, compliance and verification into
four steps made each step's job narrower and more auditable, which is a real and
measured improvement (applicability accuracy hit a perfect 1.0 in every single agent
run once the retrieval agent existed, versus 0.812-0.923 for the baseline). But
narrower steps did not make any individual step deterministic. The verifier is built
from the same stochastic material as the thing it is checking.

## Hot take: verification narrows where you are wrong, not whether you are consistent

Building a multi-agent pipeline with a dedicated verification step is a genuinely
effective way to catch a specific, nameable failure mode you already know about, like
"the compliance agent sometimes flags something as missing that is actually present."
It is not, by itself, a way to make an LLM-based system deterministic or fully
reliable. Those are different problems, and this project's evidence separates them
cleanly: applicability confusion (a systematic, nameable bug in where the baseline
looked for evidence) was fixed completely and durably by the retrieval agent's
architecture change. Temperature-0 sampling variance (a property of the underlying
model, not of any one prompt or agent boundary) was not fixed by any architecture
change attempted here, including the verification agent, because it can manifest
anywhere in the pipeline, not just in the one place verification watches.

The practical implication for anyone building this class of agent: know which kind of
unreliability you are fixing. A dedicated step with a narrow, auditable job (like this
project's deterministic, non-LLM retrieval agent, see `docs/decisions.md` M3-04) can
eliminate a whole category of error, provably, and the applicability accuracy numbers
in this project's own evaluation results show exactly that. A verification step built
from another LLM call reduces the blast radius of one specific class of mistake but
inherits the same sampling noise as everything else it touches, and reports it wasn't
asked to check will still vary between runs. If a downstream user is going to rely on
a single run of a system like this for anything consequential, the honest thing to
surface is not just a status and a confidence number per finding, but some signal of
how stable that finding was across repeated evaluation, because a compliance report
that looks identical and deterministic on the page is being generated by a process
that, this project's own numbers prove, is not.

## What worked well, also worth recording

- **Deterministic, non-LLM applicability logic.** `retrieval_agent.py`'s keyword and
  condition matching is boring, auditable Python, and it is the one component of this
  system with a perfect, unvarying track record across every recorded run.
- **Vision-based extraction was more robust to image degradation than expected.**
  UK-006 (rotated, blurred, noisy but fully compliant) had badly garbled raw OCR text
  from tesseract, yet the vision-based extraction agent still read every field
  correctly at confidence 0.9 or higher. The robustness of this system comes from the
  multimodal model call, not from the OCR text alongside it.
- **A rule pack's own documentation, once actually wired into the prompt, measurably
  changes agent behaviour.** The single largest one-time accuracy jump in the whole
  project (`RULE-IN-FOOD-007` hedging on 5 of 15 cases) came from fixing a sentence of
  English in a JSON file, not from touching any agent's code.
