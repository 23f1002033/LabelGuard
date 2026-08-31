You are the lead AI engineer and autonomous coding agent for this project.

Your job is to design and build a complete hackathon-ready MVP called:

# LabelGuard
## Global AI Product Label Compliance Auditor

Do not treat this as a generic chatbot or a simple OCR + LLM wrapper.

The core idea is:

A user uploads a packaged-product label image and selects a target market/jurisdiction. The system extracts relevant product-label information, retrieves the applicable compliance requirements, evaluates the label requirement-by-requirement, verifies important findings using evidence, and produces an actionable compliance report.

The system should be designed as a GLOBAL / MULTI-JURISDICTION concept, but the MVP must stay deliberately small enough to build and evaluate reliably in one day.

The system is a compliance ASSISTANT, not a legal authority.
Never claim that the product is legally compliant with certainty.
Every important finding should show evidence and uncertainty.
Consequential decisions should remain subject to human review.

--------------------------------------------------
0. STYLE AND WORKFLOW CONSTRAINTS (NON-NEGOTIABLE)
--------------------------------------------------

CODE STYLE:

- Do not write code comments anywhere, unless a specific line contains
  genuinely non-obvious business logic that a human reviewer would
  reasonably ask "why is this here?" about. Default to no comments.
- Do not use an em dash, en dash, smart quotes, or any other
  non-ASCII punctuation anywhere: not in code, not in commit-adjacent
  text, not in docs, not in the report UI copy. Use plain hyphens
  ("-"), straight quotes, and standard ASCII punctuation only.
- Write code the way a competent human engineer under time pressure
  would write it: direct, occasionally unpolished, no over-explained
  docstrings, no restating what the code obviously does.
- Variable and function names should read naturally, not like
  AI-generated boilerplate (avoid names like "handleDataProcessing",
  prefer specific names tied to what the thing actually is).

WORKFLOW AND VERSION CONTROL:

- Do NOT run any git commands. No git init, no git add, no git commit,
  no git branch, no git push. Version control is handled entirely
  by the developer, manually, between milestones.
- Stop completely at the end of each milestone defined in section 27.
  Do not proceed to the next milestone on your own, even if the path
  forward seems obvious. Wait for the developer to review the code,
  create a branch, and commit before you are told to continue.
- When you reach the end of a milestone, explicitly say so, summarize
  what was built and what was verified, list remaining risks, and
  stop your turn there.
- If you are unsure whether something counts as "done" for the
  current milestone, treat it as not done and say what is missing,
  rather than continuing into the next milestone's work.

--------------------------------------------------
1. HACKATHON CONTEXT
--------------------------------------------------

This project is for an agentic workflow hackathon.

The project will be judged on:

1. Problem and user value
2. Agent solution and engineering quality
3. End-to-end quality
4. Measured improvement against a fair baseline
5. Reproducibility
6. Practical insight / failure analysis

Therefore, do NOT optimize only for "working demo".

We need:

- A real user problem
- A clear bottleneck
- A meaningful agentic workflow
- A simple baseline
- A stronger final agent system
- Reproducible evaluation
- Evidence of improvement
- A short improvement changelog
- A reproducible README
- Representative agent trajectories/logs
- Good end-to-end UX

The hackathon documentation explicitly emphasizes:
- purposeful use of context/tools/memory/verification/skills/orchestration
- comparing a simple baseline against the final system
- using the same evaluation cases
- approximately 10+ evaluation cases when practical
- documenting meaningful iterations
- reproducibility from a clean environment
- showing agent trajectories and tool responses

Design the project around those requirements.

--------------------------------------------------
2. THE USER PROBLEM
--------------------------------------------------

Target users:

- small and medium product companies
- e-commerce sellers
- food/cosmetics/product manufacturers
- regulatory/compliance teams
- product managers
- exporters entering a new market
- distributors checking products before launch

Current bottleneck:

A company entering a new market may need to manually inspect:
- label images
- product information
- mandatory declarations
- warnings
- quantity information
- ingredients
- allergen statements
- manufacturer/importer information
- market-specific requirements
- readability/presentation requirements

This process is slow, repetitive, difficult to audit, and easy to miss issues in.

Our product should reduce this manual effort.

Core user question:

"Can I identify likely label-compliance issues before I launch or sell this product in a target market?"

--------------------------------------------------
3. GLOBALIZATION
--------------------------------------------------

Do NOT hard-code the system around India.

The architecture must support a jurisdiction abstraction.

For the MVP:

Use TWO jurisdictions only.

Prefer:
- India
- United Kingdom

OR another pair if reliable official public sources are easier to use.

Important:
Do not pretend that we support every regulation in an entire country.

Instead define a clearly bounded MVP scope, for example:

"Selected packaged-food label requirements for India and the UK."

The system should make it easy to add future jurisdictions via rule packs.

Concept:

rules/
    india/
       food_label_rules.json
    uk/
       food_label_rules.json

Future:

rules/
    eu/
    usa/
    canada/
    australia/
    singapore/
    uae/

The architecture must make adding a new jurisdiction mostly a data/configuration task rather than rewriting the agent system.

--------------------------------------------------
4. MVP SCOPE
--------------------------------------------------

Do NOT build every possible compliance requirement.

Keep the MVP focused.

For packaged FOOD labels, the MVP should evaluate a limited and explicit set of requirements such as:

- product name / identity
- net quantity
- ingredient information
- allergen declaration
- date-related information where applicable
- manufacturer / responsible-business information where applicable
- required warnings where applicable
- basic label readability / visibility checks if technically feasible
- other high-value mandatory declarations supported by the selected official source

Important:
The exact final checklist MUST be explicitly defined in the rule files.

Do not silently invent legal requirements.

For each rule, store structured metadata such as:

{
  "rule_id": "...",
  "jurisdiction": "...",
  "category": "...",
  "requirement": "...",
  "severity": "critical|high|medium|low",
  "source_name": "...",
  "source_url": "...",
  "source_excerpt_or_reference": "...",
  "applicability": "...",
  "validation_type": "text|vision|hybrid"
}

Only use requirements that can be supported by reliable sources.

Prefer official government/regulator sources.

--------------------------------------------------
5. HIGH-LEVEL ARCHITECTURE
--------------------------------------------------

Build the system as a small but genuine agentic workflow.

Recommended architecture:

                    PRODUCT LABEL
                         |
                         v
                +-------------------+
                | Label Extraction   |
                | Agent               |
                +-------------------+
                         |
                         v
                Structured Facts
                         |
                         v
                +-------------------+
                | Regulation         |
                | Retrieval Agent    |
                +-------------------+
                         |
                         v
                Applicable Rules
                         |
                         v
                +-------------------+
                | Compliance         |
                | Analysis Agent     |
                +-------------------+
                         |
                         v
                Candidate Findings
                         |
                         v
                +-------------------+
                | Verification       |
                | Agent              |
                +-------------------+
                         |
                         v
                Verified Findings
                         |
                         v
                +-------------------+
                | Report Generation  |
                +-------------------+
                         |
                         v
                  USER REPORT

The architecture can be simplified where useful, but do not collapse everything into one prompt.

The agent boundaries should have a clear purpose.

--------------------------------------------------
6. AGENT ROLES
--------------------------------------------------

A) LABEL EXTRACTION AGENT

Input:
- product label image(s)

Responsibilities:
- extract visible text
- identify structured fields
- identify likely ingredients
- detect quantity
- identify dates
- identify manufacturer/importer/business information
- identify warnings
- identify allergens where visible
- capture confidence
- preserve evidence references

Output should be structured JSON.

Example:

{
  "product_name": {
    "value": "...",
    "confidence": 0.96,
    "evidence": "front_label"
  },
  "net_quantity": {
    "value": "...",
    "confidence": 0.91,
    "evidence": "front_label"
  }
}

Do NOT hallucinate missing fields.

Missing should be represented as missing / unknown.

B) REGULATION RETRIEVAL AGENT

Input:
- target jurisdiction
- product category
- extracted facts if useful

Responsibilities:
- identify relevant rules from the local rule pack / knowledge base
- return only applicable rules
- preserve rule IDs and source references

Do not invent regulations.

For the MVP, a curated local rule-pack / RAG approach is preferred over a fragile live web dependency.

If external research is required while building the rule packs, prefer official government/regulator sources.

C) COMPLIANCE ANALYSIS AGENT

Input:
- extracted product facts
- applicable rules

Responsibilities:
- evaluate each rule
- determine:
  - PASS
  - FAIL
  - UNCERTAIN / NEEDS REVIEW
  - NOT APPLICABLE

For every finding provide:
- rule_id
- status
- severity
- explanation
- evidence
- confidence
- suggested fix

D) VERIFICATION AGENT

This is one of the most important parts of the project.

Its job is NOT to repeat the analysis.

It should challenge candidate findings.

For example:

Analyst:
"Allergen information appears to be missing."

Verifier:
- inspect original extracted evidence
- inspect relevant OCR text / image region if available
- check whether the rule actually applies
- check for contradiction
- reject unsupported finding if necessary

Output:

{
  "finding_id": "...",
  "verdict": "confirmed|rejected|uncertain",
  "reason": "...",
  "evidence": [...]
}

Only verified or clearly qualified findings should appear as high-confidence final findings.

E) REPORT GENERATOR

Generate a professional report containing:

- product
- target jurisdiction
- overall compliance summary
- score or status
- passed requirements
- failed requirements
- uncertain requirements
- severity
- evidence
- source references
- recommended corrections
- explicit disclaimer that this is an AI-assisted review and not legal advice

--------------------------------------------------
7. IMPORTANT DESIGN PRINCIPLE:
EVIDENCE FIRST
--------------------------------------------------

Never allow the final report to contain unsupported claims.

Every finding should follow:

CLAIM
  ->
EVIDENCE
  ->
RULE
  ->
VERIFICATION
  ->
FINAL STATUS

Example:

Finding:
"Allergen declaration may be missing."

Evidence:
"No allergen statement detected in extracted label text."

Applicable rule:
RULE-UK-FOOD-004

Verification:
"Reviewer agent checked OCR result and image evidence."

Final:
"Needs review"

This evidence-chain is a core differentiator.

--------------------------------------------------
8. BASELINE SYSTEM
--------------------------------------------------

Build a separate baseline implementation.

The baseline should be intentionally simple and fair.

Recommended baseline:

Image
  ->
OCR / Vision extraction
  ->
Single LLM prompt
  ->
Compliance report

No specialized verification agent.

No sophisticated orchestration.

No separate analyst/verifier roles.

The baseline and final agent must receive:
- the same input cases
- the same relevant rule information
- comparable model/resources where practical

The baseline exists to measure improvement.

Do NOT make the baseline artificially bad.

It should represent a reasonable naive implementation.

--------------------------------------------------
9. FINAL AGENT SYSTEM
--------------------------------------------------

Final system:

Image
  ->
Extraction Agent
  ->
Rule Retrieval / Selection
  ->
Compliance Agent
  ->
Verification Agent
  ->
Evidence-backed Report

The final system should improve at least some of:

- finding accuracy
- false positive rate
- evidence grounding
- requirement coverage
- consistency
- human review time
- structured output quality

--------------------------------------------------
10. EVALUATION DATASET
--------------------------------------------------

Create a small reproducible evaluation suite.

Target:
10-15 test cases.

Do NOT rely on random ad-hoc testing.

Create structured evaluation cases such as:

1. Clean / compliant label
2. Missing quantity
3. Missing ingredient information
4. Missing allergen declaration
5. Missing business information
6. Warning issue
7. Multiple simultaneous violations
8. Ambiguous label
9. Hard-to-read label
10. Fully compliant but visually complex label
11. Cross-jurisdiction difference
12. Challenging false-positive case

Use synthetic labels if necessary.

Prefer synthetic evaluation data because it is reproducible and safe.

Document each case:

{
  "case_id": "...",
  "jurisdiction": "...",
  "image": "...",
  "expected_findings": [...],
  "expected_status": "...",
  "notes": "..."
}

The dataset must include at least one difficult/challenging case.

--------------------------------------------------
11. PRIMARY METRIC
--------------------------------------------------

Choose ONE primary metric.

Recommended:

"Requirement-level detection F1 score"

or, if implementation makes that difficult:

"Verified finding precision"

Secondary metrics may include:

- recall
- false positive rate
- evidence accuracy
- requirement coverage
- average human review time
- runtime
- estimated API cost

Be rigorous.

Do not create fake benchmark numbers.

All metrics must be generated from actual evaluation runs.

--------------------------------------------------
12. EVALUATION PIPELINE
--------------------------------------------------

Create a script that can run:

python evaluate.py --system baseline

and:

python evaluate.py --system agent

The evaluation should:

1. load test cases
2. run the selected system
3. normalize outputs
4. compare against expected annotations
5. compute metrics
6. save results
7. generate a summary table

Example output:

Baseline:
Precision: ...
Recall: ...
F1: ...

Agent:
Precision: ...
Recall: ...
F1: ...

Improvement:
...

Also record:
- runtime
- approximate cost if measurable
- failures
- verifier rejections

--------------------------------------------------
13. IMPROVEMENT CHANGELOG
--------------------------------------------------

Create:

IMPROVEMENT_CHANGELOG.md

Use this structure:

Stage | What changed | Why | Evidence | Decision

Start with:

Baseline
Iteration 1
Iteration 2
Iteration 3
Final

Make the iterations real.

Do not fabricate experiments.

Possible genuine iterations:

- baseline single-agent approach
- adding structured extraction
- adding jurisdiction-specific rule packs
- adding verification agent
- changing context supplied to compliance agent
- improving evidence tracking
- removing an approach that caused more false positives

For every meaningful experiment:
- state what was changed
- run evaluation
- record results
- decide whether to keep/remove it

--------------------------------------------------
14. REQUIRED FAILURE ANALYSIS
--------------------------------------------------

At the end identify the main failure mode.

Examples:

- OCR misses small text
- image perspective causes extraction errors
- ambiguous applicability of a rule
- agent incorrectly assumes a requirement applies
- evidence grounding fails
- verification catches some but not all errors

Choose the ACTUAL biggest failure mode from observed experiments.

Then write a practical "Hot Take":

"What we learned about building reliable agents for this class of task."

Do not invent this insight before evaluation.

--------------------------------------------------
15. UI
--------------------------------------------------

Build a clean minimal web interface.

Recommended stack:

Frontend:
- React / Next.js
- Tailwind if useful

Backend:
- Python
- FastAPI

Agent orchestration:
- use the most practical framework already available in the environment
- if no framework is necessary, use a clean Python orchestration layer

Do not add unnecessary infrastructure.

UI flow:

1. Upload product label
2. Choose jurisdiction
3. Choose product category
4. Analyze
5. Show progress / agent stages
6. Show final report

The report should have:

- compliance score/status
- summary
- passed items
- failed items
- uncertain items
- severity
- evidence
- source
- recommendation

Also provide a simple "agent trace" / "analysis steps" panel suitable for the demo.

Do not expose hidden chain-of-thought.

Show only safe, high-level workflow events such as:

"Extracted label fields"
"Selected applicable rules"
"Generated candidate findings"
"Verified findings"
"Generated final report"

--------------------------------------------------
16. PROJECT STRUCTURE
--------------------------------------------------

Use a clean structure similar to:

labelguard/
|
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── agents/
│   │   │   ├── extraction_agent.py
│   │   │   ├── retrieval_agent.py
│   │   │   ├── compliance_agent.py
│   │   │   ├── verification_agent.py
│   │   │   └── report_agent.py
│   │   ├── models/
│   │   ├── services/
│   │   └── config.py
│   │
│   └── tests/
│
├── frontend/
│
├── rules/
│   ├── india/
│   └── uk/
│
├── evaluation/
│   ├── cases/
│   ├── annotations/
│   ├── baseline/
│   ├── agent/
│   └── evaluate.py
│
├── docs/
│   ├── architecture.md
│   ├── evaluation.md
│   └── agent_traces.md
│
├── scripts/
│
├── README.md
├── IMPROVEMENT_CHANGELOG.md
├── requirements.txt / pyproject.toml
├── .env.example
└── docker-compose.yml (only if genuinely useful)

You can adjust this structure if the repository already contains a better architecture.

--------------------------------------------------
17. DEVELOPMENT PRINCIPLES
--------------------------------------------------

CRITICAL:

Do not blindly create files before understanding the repository.

FIRST:
- inspect the repository
- inspect package files
- inspect existing README
- inspect configuration
- inspect available dependencies
- inspect current implementation
- identify what already exists

Then create a concise implementation plan.

Before making major architectural changes, explain the plan in the development notes.

Prefer:
- simple
- modular
- testable
- reproducible
- easy to demo

Avoid:
- Kubernetes
- microservices
- unnecessary vector databases
- complicated cloud deployment
- massive frameworks
- custom model training
- long-running infrastructure
- unnecessary abstractions

This is a one-day hackathon MVP.

--------------------------------------------------
18. MODEL / API STRATEGY
--------------------------------------------------

Use practical existing models/APIs.

Do not train models from scratch.

Keep provider/model configuration environment-based.

Example:

LLM_PROVIDER=...
LLM_MODEL=...

Do not hard-code API keys.

Create:

.env.example

Never commit secrets.

If external APIs are expensive or unreliable:
- create a deterministic mock mode
- make the project runnable with mock/demo data
- ensure evaluation can still run reproducibly where possible

--------------------------------------------------
19. RULE SOURCES
--------------------------------------------------

For real regulatory claims:

Prefer official sources from:
- government departments
- regulators
- legislation portals
- official guidance pages

Do not use random blogs as authoritative regulatory sources.

Every rule should have:
- source name
- URL
- rule reference
- applicability scope
- date/version if available

Do not silently infer a law from a vague source.

For any uncertain legal interpretation:
mark the requirement as:
"Needs professional review"

--------------------------------------------------
20. TESTING
--------------------------------------------------

Write automated tests for:

- rule parsing
- extraction normalization
- missing fields
- rule applicability
- compliance status logic
- evidence mapping
- verification behavior
- report generation
- API endpoints
- evaluation metric calculations

At minimum ensure:

- backend starts
- frontend starts
- a demo label can be analyzed
- baseline runs
- final agent runs
- evaluation runs
- tests pass

Add edge-case tests.

--------------------------------------------------
21. DEMO MODE
--------------------------------------------------

Create a deterministic demo mode.

The user should be able to run the project and immediately test it without needing a complex external setup.

Provide:

- demo label image(s)
- demo rule packs
- demo output
- demo evaluation command

Recommended:

python scripts/demo.py

or equivalent.

This should run a complete end-to-end workflow.

--------------------------------------------------
22. REPRODUCIBILITY
--------------------------------------------------

README must contain exact commands from a clean environment.

Include:

1. prerequisites
2. installation
3. environment variables
4. model/API setup
5. starting backend
6. starting frontend
7. running demo
8. running baseline
9. running final agent
10. running evaluation
11. running tests
12. expected output
13. approximate runtime
14. approximate cost where applicable

The goal is:

A different person should be able to clone the project and reproduce the main result.

--------------------------------------------------
23. AGENT TRAJECTORY LOGGING
--------------------------------------------------

The hackathon asks for representative agent trajectories.

Therefore implement structured logs.

For each agent execution capture safe metadata such as:

{
  "agent": "verification_agent",
  "step": "verify_finding",
  "input_reference": "...",
  "tool_used": "...",
  "result": "...",
  "decision": "confirmed",
  "timestamp": "..."
}

Do NOT log:
- API secrets
- personal information
- hidden chain-of-thought
- private credentials

Create a demo-friendly trace file.

Example:

evaluation/traces/case_001.json

--------------------------------------------------
24. SECURITY AND DATA HANDLING
--------------------------------------------------

Do not store uploaded user images permanently by default.

Use temporary storage or demo storage.

Do not log secrets.

Validate uploads.

Restrict file types.

Protect API endpoints reasonably.

Clearly state data handling in README.

--------------------------------------------------
25. REPORT QUALITY
--------------------------------------------------

The final report must NOT feel like raw AI output.

It should look like a professional compliance review.

Suggested structure:

# LabelGuard Compliance Report

Product:
Jurisdiction:
Product Category:

Overall Assessment:
PASS / FAIL / NEEDS REVIEW

## Summary

X requirements passed
Y failed
Z uncertain

## Critical / High Risk Findings

Finding
Rule
Evidence
Confidence
Recommended action

## Passed Requirements

...

## Needs Review

...

## Sources

...

## Disclaimer

This report is an AI-assisted preliminary compliance review.
It is not legal advice and does not replace review by a qualified professional or regulator.

--------------------------------------------------
26. WHAT NOT TO DO
--------------------------------------------------

DO NOT:

- claim universal legal compliance
- claim support for every country
- fabricate legal requirements
- fabricate evaluation improvements
- make up benchmark numbers
- use a giant single prompt and call it multi-agent
- create agents that do not have distinct purposes
- over-engineer the architecture
- train a custom model
- make unnecessary cloud infrastructure
- leave the project impossible to reproduce
- hard-code API secrets
- depend completely on live internet access for the demo

--------------------------------------------------
27. IMPLEMENTATION ORDER (MILESTONES)
--------------------------------------------------

Work through the following milestones IN ORDER. Stop completely at
the end of each one and wait for the developer, per section 0. Do
not start the next milestone until explicitly told to continue.

MILESTONE 1 - INSPECTION AND DESIGN
- inspect repository (if one exists), stack, current files, constraints
- finalize MVP scope
- define rule schema
- define agent interfaces
- define evaluation schema
Deliverable: a short written plan plus any schema/config files.
No application code yet unless it is purely scaffolding.
STOP HERE. Wait for developer review, branch, and commit.

MILESTONE 2 - BASELINE
- implement the baseline (single-agent) system
- build the first batch of evaluation cases
- run baseline metrics
Deliverable: working baseline, first real evaluation numbers.
STOP HERE. Wait for developer review, branch, and commit.

MILESTONE 3 - CORE AGENT SYSTEM AND INTEGRATION
- extraction agent
- rule retrieval/selection
- compliance agent
- verification agent
- report generator
- backend API
- frontend
- full end-to-end workflow wired together
Deliverable: a working end-to-end app, upload to report.
STOP HERE. Wait for developer review, branch, and commit.

MILESTONE 4 - EVALUATION AND ITERATION
- complete the 10-15 evaluation cases
- run baseline and final agent through the same evaluation
- calculate metrics, compare
- inspect failures, identify the largest failure mode
- make at least one genuine iteration based on that finding
- re-run evaluation and record the result
Deliverable: real baseline vs agent comparison, at least one
documented iteration with before/after numbers.
STOP HERE. Wait for developer review, branch, and commit.

MILESTONE 5 - POLISH AND FINAL AUDIT
- tests across the checklist in section 20
- README with exact reproducible commands
- IMPROVEMENT_CHANGELOG.md
- demo mode
- agent trajectory trace files
- failure analysis and hot take (section 14)
- final audit: does everything actually run from clean, are metrics
  real, are rules sourced, are findings evidence-backed, is the demo
  understandable in under 5 minutes
Deliverable: submission-ready project.
STOP HERE. Wait for developer review, branch, and commit.

--------------------------------------------------
28. IMPORTANT AUTONOMOUS CODING BEHAVIOUR
--------------------------------------------------

You are allowed to modify files directly.

However:

1. Inspect before editing.
2. Keep changes incremental.
3. Run tests after meaningful changes.
4. Fix failures instead of hiding them.
5. Do not delete working functionality without reason.
6. Do not invent missing information.
7. If an assumption is necessary, make it explicit in a project note.
8. Prefer the simplest implementation that satisfies the requirement.
9. Keep the project runnable after every milestone.
10. Do not run git commands. Do not proceed past a milestone boundary
    without being told to continue, per section 0.

When blocked:
- investigate the actual issue
- choose the simplest robust alternative
- document the decision

Do not spend excessive time making the architecture theoretically perfect.

The goal is a strong, working, reproducible hackathon submission.

--------------------------------------------------
29. START NOW
--------------------------------------------------

Your first response/action must NOT immediately generate the whole application.

Begin with MILESTONE 1 only:

A) Inspect the repository thoroughly (if one exists).

B) Summarize:
- current stack
- existing functionality
- relevant files
- dependencies
- constraints

C) Propose the exact MVP scope.

D) Propose:
- architecture
- agent responsibilities
- data structures
- evaluation design
- rule-pack design

E) Identify what can realistically be completed within one day.

F) Then produce Milestone 1's scaffolding/config deliverables only.

At the end of Milestone 1:
- show what changed
- show what works
- show remaining risks
- explicitly stop and say you are waiting for review, branch, and
  commit before continuing to Milestone 2

Do not continue past this point on your own.

The final result should be a serious engineering project, not a toy chatbot.

PROJECT NAME:
LabelGuard

TAGLINE:
AI-powered global product label compliance auditing with evidence-backed verification.

PRIMARY VALUE:
Reduce the manual effort and missed issues involved in checking product labels against market-specific requirements.

PRIMARY TECHNICAL DIFFERENTIATOR:
Specialized agent workflow + jurisdiction-aware rule packs + evidence-backed verification.

PRIMARY EVALUATION QUESTION:
Does the verification-oriented agent workflow produce more accurate and better-grounded compliance findings than a reasonable single-agent baseline?

Now inspect the repository and begin with MILESTONE 1.
