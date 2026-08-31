# Improvement changelog

Every row records a real change and, from Milestone 2 onward, the evaluation numbers
that justified keeping or dropping it. No number in this file is written by hand; each
one comes from an `evaluation/evaluate.py` run and names the model, mode, case count
and date.

| Stage | What changed | Why | Evidence | Decision |
| --- | --- | --- | --- | --- |
| M1 setup | Rule packs for India and the UK, rule and evaluation schemas, agent interfaces, schema validator | Give both the baseline and the agent identical, sourced requirements so any later difference is attributable to the workflow and not to the rule text | `scripts/validate_schemas.py` passes: 2 rule packs, 25 rules, all sources cited with URL and excerpt | Kept |
| Baseline | pending Milestone 2 | | | |
| Iteration 1 | pending Milestone 4 | | | |
| Final | pending Milestone 5 | | | |
