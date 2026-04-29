# Causal Decision Debugger — Build Specification

> **Historical document.** This spec describes the original pre-plugin design. The shipped layout differs: skill assets live at `skills/causal-decision-debugger/` (not `.claude/skills/...`), agents at `agents/` (not `.claude/agents/...`), and there is a packaged `causal-debugger` CLI plus a bundled wheel under `skills/causal-decision-debugger/vendor/`. For the current structure and entry points, see `README.md` and `CLAUDE.md` — those are authoritative; this spec captures the rationale and method coverage but not the final paths.

## 0. Purpose of This Document

This document is a build-ready specification for an AI coding agent. It describes the product concept, architecture, Claude Code Skill integration, future standalone CLI, agent workflow, artifacts, data safety model, method-selection logic, and implementation roadmap for a causal inference assistant aimed at engineers, data scientists, product managers, and business teams.

The system should help users move from weak correlation-based thinking to decision-grade causal reasoning. It should not merely generate causal graphs. It should help teams answer practical questions such as:

- Did this product change cause retention to improve?
- Did this marketing campaign create incremental revenue?
- Did this pricing change hurt conversion?
- Why did a key metric drop last week?
- Which user segments benefited from an intervention?
- Can the current data answer this causal question at all?
- What experiment or rollout design should we use next time?

The recommended implementation path is:

```text
Claude Code Skill MVP
  → Script-backed Skill
  → CLI-backed Skill
  → Standalone CLI usable by any agent system
```

The first version should be implemented as a **Claude Code Agent Skill** because it integrates quickly with users' existing agentic workflows, cloud credentials, local repositories, dbt projects, SQL files, and warehouse tools. The long-term system should extract deterministic pieces into a standalone CLI for portability, reproducibility, and enterprise trust.

---

## 1. Product Vision

### 1.1 One-line Vision

**A causal decision debugging system that lets AI coding agents investigate real business questions inside a company's existing data environment, producing auditable causal specs, assumptions, estimates, robustness checks, and decision reports.**

### 1.2 Product Positioning

Do **not** position the product as:

> “Upload a CSV and generate a causal graph.”

Instead, position it as:

> “Turn business events into decision-grade causal evidence.”

Or:

> “A causal review system for product, growth, engineering, and business decisions.”

Or:

> “Grammarly for causal claims + Copilot for causal analysis + GitHub review for assumptions.”

### 1.3 Core Philosophy

The system should treat causal inference like **debugging reality**.

Engineers already understand questions like:

- What changed?
- When did it change?
- Who was affected?
- Who was not affected?
- What else changed at the same time?
- Did the bug happen before or after the deploy?
- Is there a comparable control group?

These are causal questions. The system should translate business ambiguity into clear causal structure.

### 1.4 Core Differentiator

The system should not be a generic AutoML-for-causality tool. It should be a **decision-first causal reasoning assistant** that:

1. Translates business questions into causal questions.
2. Interviews users for domain knowledge.
3. Audits available data.
4. Builds an assumption ledger.
5. Drafts a DAG when useful.
6. Selects a suitable causal design.
7. Runs appropriate EDA, estimation, and robustness checks.
8. Says “not identifiable” when appropriate.
9. Produces decision-grade reports.
10. Recommends future experiment or rollout designs.

---

## 2. Why This Should Be Skill-first, Then CLI

### 2.1 Problem With Standalone Web Apps

A standalone web app requiring CSV upload is weak for real business use because:

- Data is too large for manual upload.
- Data is sensitive.
- Data is spread across many tables.
- Users often do not know which CSV to upload.
- Metric definitions live in dbt, LookML, SQL, notebooks, dashboards, or code.
- Rollout history may live in GitHub, LaunchDarkly, Jira, logs, or config files.
- Analysis requires iterative queries.
- The final answer must be reproducible and reviewable.

### 2.2 Why Claude Code Skill First

Claude Code already provides:

- Terminal-native agent environment.
- File reading/writing.
- Shell execution.
- Codebase awareness.
- Project context.
- Subagents.
- Tool permissions.
- MCP integrations.
- User-side authentication.
- Existing developer workflow.

Therefore, the first product should live inside Claude Code as an Agent Skill.

### 2.3 Why a Standalone CLI Later

A standalone CLI becomes important for:

- Deterministic execution.
- Portability outside Claude Code.
- Use by Codex, Cursor, Devin-like agents, CI, GitHub Actions, and internal agents.
- Enterprise governance.
- Standardized audit logs.
- Reproducible commands.
- Policy enforcement.
- Better testing.

### 2.4 Final Strategy

Build a Claude Code Skill first, but structure it around portable artifacts and deterministic scripts so the CLI can emerge naturally.

```text
Skill = UX, workflow, subagent orchestration, causal reasoning instructions.
Scripts/CLI = deterministic validation, profiling, estimation, refutation, report rendering.
```

---

## 3. Target Users and Use Cases

### 3.1 Primary Users

- Software engineers.
- Data scientists.
- Product managers.
- Growth teams.
- Game economy teams.
- Marketplace teams.
- Recommendation/search teams.
- Business analysts.

### 3.2 Initial Product Wedge

Start with **Causal Product Analytics**.

This is more practical than “general causal inference.” Product and growth teams ask causal questions constantly and often lack clean experiments.

### 3.3 Initial Use Cases

1. Feature launch impact.
2. Campaign incrementality.
3. Retention drop investigation.
4. Ranking/recommendation change impact.
5. Pricing or coupon effect.
6. Marketplace supply/demand intervention.
7. A/B test sanity check.
8. Experiment design before launch.
9. Causal claim review in documents or pull requests.

### 3.4 Example User Prompts

```text
Investigate whether onboarding_v2 improved D7 retention.
Use BigQuery through the existing project tools.
Do not export PII.
Keep query cost low.
Generate a business report and technical appendix.
```

```text
Use the causal decision debugger to determine whether the March pricing change caused conversion to drop.
```

```text
Review this launch claim: “The new ranking algorithm increased GMV.” Check whether the evidence supports a causal claim.
```

```text
Design a measurement plan for next month's battle-pass discount experiment.
```

---

## 4. High-level System Architecture

### 4.1 Skill-first Architecture

```text
User in Claude Code
        ↓
Causal Decision Debugger Skill
        ↓
Claude Code subagents
        ↓
Existing project tools and credentials
BigQuery / AWS / Snowflake / dbt / SQL files / logs / dashboards
        ↓
Local deterministic scripts
        ↓
Portable artifacts
causal_spec.yaml / assumption_ledger.yaml / method_plan.json / report.md
```

### 4.2 Long-term Hybrid Architecture

```text
Claude Code Skill
  = orchestration, user interaction, workflow, report writing

Standalone CLI / Python package
  = deterministic validation, profiling, estimation, robustness checks, rendering

Warehouse connectors
  = BigQuery, Athena, Redshift, Snowflake, local parquet/csv

Artifacts
  = causal_spec.yaml, assumption_ledger.yaml, dag.json, estimates.json, report.md
```

### 4.3 Long-term Standalone CLI Architecture

```text
User's agent system
Claude Code / Codex / Cursor Agent / internal agent
        ↓
causal CLI
causal ask / causal inspect / causal plan / causal run / causal report
        ↓
User's existing data tools
BigQuery / Athena / Redshift / Snowflake / dbt / S3 / local parquet
        ↓
Local artifacts and reports
```

---

## 5. Causal Workflow

The system must follow this workflow unless the user explicitly requests a narrower task.

### 5.1 Required Workflow

1. Clarify the decision.
2. Translate the business question into a causal question.
3. Create or update `causal_spec.yaml`.
4. Identify treatment, outcome, unit, treatment time, outcome window, and comparison group.
5. Discover relevant data sources.
6. Ask targeted domain questions.
7. Inspect data quality and schema.
8. Check timestamp order and leakage risk.
9. Identify pre-treatment covariates.
10. Identify forbidden post-treatment variables.
11. Build an assumption ledger.
12. Draft a DAG if useful.
13. Select causal design and estimation methods.
14. Run EDA and balance checks.
15. Run estimation if data supports it.
16. Run robustness/refutation checks.
17. Generate business report.
18. Generate technical appendix.
19. Recommend next action or future experiment design.

### 5.2 Workflow Diagram

```text
Business Question Agent
        ↓
Causal Spec Agent
        ↓
Domain Interview Agent
        ↓
Data Scout / EDA Agent
        ↓
DAG + Assumption Ledger Agent
        ↓
Method Selection Agent
        ↓
Estimation Agent
        ↓
Refutation / Sensitivity Agent
        ↓
Decision Report Agent
        ↓
Experiment Design Agent
```

---

## 6. Claude Code Skill Implementation

### 6.1 Proposed Repository Structure

```text
.claude/
  skills/
    causal-decision-debugger/
      SKILL.md
      reference/
        method-router.md
        assumption-ledger.md
        report-template.md
        causal-spec-schema.md
        sql-safety-rules.md
        causal-glossary.md
      scripts/
        validate_causal_spec.py
        profile_dataframe.py
        check_timestamps.py
        check_balance.py
        suggest_method.py
        generate_report.py
      templates/
        causal_spec.yaml
        assumption_ledger.yaml
        method_plan.json
        report.md
        technical_appendix.md
  agents/
    data-scout.md
    sql-safety-reviewer.md
    causal-methodologist.md
    assumption-ledger-agent.md
    report-writer.md
```

### 6.2 `SKILL.md` Draft

Create `.claude/skills/causal-decision-debugger/SKILL.md`:

```markdown
---
name: Causal Decision Debugger
description: Use this when the user asks whether a product, business, marketing, pricing, ranking, onboarding, marketplace, policy, or engineering change caused a metric change. Helps translate business questions into causal specs, inspect data, select causal inference methods, run checks, and generate decision-grade reports.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Causal Decision Debugger

## Goal

Help users move from correlation-based claims to careful causal claims with explicit assumptions, data checks, estimates, robustness checks, and recommended next actions.

## Required workflow

1. Clarify the decision and causal question.
2. Create or update `causal_spec.yaml`.
3. Identify unit, treatment, outcome, treatment time, outcome window, and comparison group.
4. Inspect available data through existing project tools.
5. Check timestamp order and leakage risk.
6. Identify pre-treatment covariates and forbidden post-treatment variables.
7. Build `assumption_ledger.yaml`.
8. Select a method and write `method_plan.json`.
9. Generate safe SQL drafts when needed.
10. Ask the user before running expensive or risky queries.
11. Run EDA, balance checks, estimation, and robustness checks where possible.
12. Produce `report.md` and `technical_appendix.md`.

## Behavioral rules

- Be decision-first, not graph-first.
- Be conservative with causal claims.
- Never claim causality without assumptions.
- Explicitly say “not identifiable” when the data cannot answer the question.
- Separate confirmed facts, user-provided assumptions, data-suggested patterns, and model/LLM-suggested hypotheses.
- Never control for post-treatment variables.
- Always check timestamp order.
- Always warn about unobserved confounding when relevant.
- Prefer reproducible artifacts over one-off chat answers.
- Avoid exporting PII.
- Prefer aggregated or sampled data for exploration.
- Use dry runs or cost checks before warehouse queries when available.

## Output artifacts

Place artifacts under:

`analysis/<analysis_id>/`

Required files:

- `causal_spec.yaml`
- `assumption_ledger.yaml`
- `data_sources.yaml`
- `method_plan.json`
- `report.md`
- `technical_appendix.md`

Optional files:

- `dag.json`
- `queries/*.sql`
- `artifacts/eda_summary.json`
- `artifacts/balance_check.json`
- `artifacts/estimates.json`
- `artifacts/robustness.json`
```

### 6.3 Skill Variants

Eventually support two Skill modes:

```text
causal-readonly
causal-full
```

`causal-readonly`:

- Inspects files and schemas.
- Drafts SQL.
- Creates causal spec and reports.
- Does not run expensive queries without explicit approval.

`causal-full`:

- Can run local scripts.
- Can run approved queries.
- Can generate estimates and full reports.

---

## 7. Claude Code Subagents

### 7.1 `data-scout`

Create `.claude/agents/data-scout.md`:

```markdown
---
name: data-scout
description: Finds relevant tables, schemas, SQL files, dbt models, dashboards, event definitions, and data sources for causal analysis.
tools: Read, Grep, Glob, Bash
---

You are a data discovery specialist for causal analysis.

Your job:
- Find candidate data sources relevant to the causal question.
- Look for treatment, outcome, user/entity unit, timestamps, covariates, experiment assignment, rollout logs, and metric definitions.
- Prefer existing semantic definitions such as dbt models, LookML, metric YAML, notebooks, or SQL files.
- Do not run expensive queries without approval.
- Do not export PII.

Output YAML:

candidate_sources:
  - name: string
    type: table | file | dbt_model | sql | dashboard | log | config
    path_or_identifier: string
    relevance: high | medium | low
    reason: string
    key_fields:
      - string
risks:
  - string
next_questions:
  - string
```

### 7.2 `sql-safety-reviewer`

Create `.claude/agents/sql-safety-reviewer.md`:

```markdown
---
name: sql-safety-reviewer
description: Reviews SQL for safety, query cost, PII leakage, accidental writes, full scans, timestamp mistakes, and causal-analysis correctness.
tools: Read, Grep, Glob, Bash
---

You are a SQL safety and causal validity reviewer.

Check SQL for:
- Accidental writes or mutations.
- Full table scans without date filters.
- Excessive cost risk.
- Raw PII export.
- Missing unit-level deduplication.
- Treatment after outcome mistakes.
- Post-treatment covariates being used as controls.
- Incorrect joins that duplicate units.
- Missing eligibility definition.
- Missing comparison group.

Output YAML:

approved: true | false
risk_level: low | medium | high
issues:
  - severity: low | medium | high
    description: string
    suggested_fix: string
```

### 7.3 `causal-methodologist`

Create `.claude/agents/causal-methodologist.md`:

```markdown
---
name: causal-methodologist
description: Selects appropriate causal designs and methods based on question, data structure, treatment assignment, timing, and assumptions.
tools: Read, Grep, Glob, Bash
---

You are a conservative causal inference methodologist.

Choose methods based on design, not model fashion.

Prefer:
- A/B test analysis for randomized assignment.
- Difference-in-differences for staggered or group/time rollouts with pre-periods.
- Interrupted time series for aggregate time-series interventions without good controls.
- Synthetic control for treated unit/group with donor pool.
- Regression discontinuity for threshold-based assignment.
- Instrumental variables for imperfect compliance or encouragement designs.
- Propensity score weighting/matching or doubly robust estimation for observational user-level treatments with rich pre-treatment covariates.
- Causal forest / CATE methods for heterogeneous treatment effects.
- Root-cause analysis for metric drops.
- “Not identifiable” when the design cannot support causal estimation.

Output JSON:

{
  "primary_method": "string",
  "secondary_methods": ["string"],
  "required_assumptions": ["string"],
  "diagnostics": ["string"],
  "refutation_tests": ["string"],
  "identifiability_status": "identifiable | weakly_identifiable | not_identifiable",
  "reasoning_summary": "string"
}
```

### 7.4 `assumption-ledger-agent`

Create `.claude/agents/assumption-ledger-agent.md`:

```markdown
---
name: assumption-ledger-agent
description: Converts user answers, data checks, and causal structure into explicit assumptions with status, evidence, risk, and needed follow-up.
tools: Read, Grep, Glob, Bash
---

You maintain the assumption ledger for causal analysis.

Classify assumptions as:
- confirmed
- plausible
- uncertain
- weak
- violated
- unknown

Track evidence and risk.

Output YAML:

assumptions:
  - id: string
    name: string
    status: confirmed | plausible | uncertain | weak | violated | unknown
    importance: low | medium | high | critical
    evidence: string
    risk_if_false: string
    how_to_check_or_improve: string
```

### 7.5 `report-writer`

Create `.claude/agents/report-writer.md`:

```markdown
---
name: report-writer
description: Writes business-readable causal reports and technical appendices from causal specs, data audits, method plans, estimates, and assumptions.
tools: Read, Write, Edit
---

You write decision-grade causal reports.

Report style:
- Clear, conservative, and business-readable.
- Do not overclaim.
- Separate conclusion, evidence, assumptions, limitations, and recommended next actions.
- Always include confidence level.
- Always state whether the result is causal, associational, weakly causal under assumptions, or not identifiable.

Required sections:
1. Executive Summary
2. Decision Context
3. Causal Question
4. Data Used
5. Method Summary
6. Main Result
7. Assumption Ledger Summary
8. Robustness and Refutation Checks
9. Limitations
10. Recommended Decision
11. Recommended Next Experiment or Data Collection
12. Technical Appendix Link
```

---

## 8. Core Artifacts

Artifacts are the product moat. Every analysis should be saved under:

```text
analysis/<analysis_id>/
```

Recommended structure:

```text
analysis/onboarding_retention_2026_03/
  causal_spec.yaml
  assumption_ledger.yaml
  data_sources.yaml
  method_plan.json
  dag.json
  queries/
    001_schema_discovery.sql
    002_population.sql
    003_treatment_outcome.sql
    004_covariates.sql
  artifacts/
    eda_summary.json
    balance_check.json
    timestamp_check.json
    estimates.json
    robustness.json
  report.md
  technical_appendix.md
```

### 8.1 `causal_spec.yaml`

This is the most important artifact.

```yaml
analysis_id: onboarding_retention_2026_03

status: draft
created_by: causal-decision-debugger

business_decision:
  question: "Should we keep onboarding_v2?"
  owner: "growth_team"
  action_options:
    - keep
    - rollback
    - run_followup_experiment

causal_question:
  question: "What is the effect of onboarding_v2 exposure on D7 retention?"
  unit: user
  treatment:
    name: onboarding_v2_exposed
    type: binary
    treatment_time: onboarding_started_at
  outcome:
    name: retained_d7
    type: binary
    outcome_window: "signup_at + 7 days"
  comparison_group: "eligible users not exposed to onboarding_v2"

population:
  eligibility_definition: "new users who signed up during rollout window"
  inclusion_criteria:
    - "has signup timestamp"
    - "eligible for onboarding experience"
  exclusion_criteria:
    - "internal test accounts"
    - "users with missing signup timestamp"

data:
  warehouse: bigquery
  project: null
  dataset: null
  population_query: queries/002_population.sql
  treatment_outcome_query: queries/003_treatment_outcome.sql
  covariate_query: queries/004_covariates.sql

variables:
  pre_treatment_covariates:
    - country
    - device_type
    - acquisition_channel
    - signup_week
  forbidden_post_treatment_variables:
    - tutorial_completed
    - first_purchase_after_signup
    - session_count_after_treatment
  suspected_unobserved_confounders:
    - user_motivation
    - prior_brand_awareness

assumptions:
  no_unobserved_confounding:
    status: uncertain
    notes: "User motivation is not directly observed."
  treatment_precedes_outcome:
    status: confirmed
  no_simultaneous_major_change:
    status: unknown
  positivity_overlap:
    status: unknown
  stable_unit_treatment_value:
    status: plausible

methods:
  primary: null
  secondary: []
  robustness: []
```

### 8.2 `assumption_ledger.yaml`

```yaml
assumptions:
  - id: A1
    name: Treatment happened before outcome
    status: confirmed
    importance: critical
    evidence: "onboarding_started_at occurs before D7 retention window"
    risk_if_false: "Analysis would contain time leakage"
    how_to_check_or_improve: "Validate timestamp ordering for every user"

  - id: A2
    name: No major simultaneous change
    status: unknown
    importance: high
    evidence: "No rollout calendar has been checked yet"
    risk_if_false: "Metric change may be caused by another launch or campaign"
    how_to_check_or_improve: "Ask PM/engineer and inspect release logs"

  - id: A3
    name: No unobserved confounding after adjustment
    status: weak
    importance: critical
    evidence: "Acquisition channel, country, device, and signup week are available, but user motivation is not"
    risk_if_false: "Estimated effect may reflect selection bias"
    how_to_check_or_improve: "Run randomized holdout or add better intent proxies"
```

### 8.3 `method_plan.json`

```json
{
  "identifiability_status": "weakly_identifiable",
  "primary_method": "doubly_robust_estimation",
  "secondary_methods": [
    "propensity_score_weighting",
    "matching"
  ],
  "required_assumptions": [
    "no_unobserved_confounding",
    "positivity_overlap",
    "treatment_precedes_outcome"
  ],
  "diagnostics": [
    "covariate_balance_check",
    "propensity_overlap_check",
    "timestamp_order_check",
    "missingness_check"
  ],
  "refutation_tests": [
    "placebo_outcome",
    "placebo_treatment",
    "subset_stability",
    "sensitivity_to_unobserved_confounding"
  ],
  "reasoning_summary": "Treatment was not confirmed randomized, but user-level pre-treatment covariates are available. A doubly robust estimator is appropriate if overlap is acceptable and confounding assumptions are plausible."
}
```

### 8.4 `data_sources.yaml`

```yaml
candidate_sources:
  - name: analytics.users
    type: table
    relevance: high
    reason: "Contains signup timestamp, country, device, acquisition channel"
    key_fields:
      - user_id
      - signup_at
      - country
      - device_type
      - acquisition_channel

  - name: analytics.onboarding_events
    type: table
    relevance: high
    reason: "Contains onboarding_v2 exposure events"
    key_fields:
      - user_id
      - event_name
      - event_timestamp
      - onboarding_version

  - name: analytics.retention_daily
    type: table
    relevance: high
    reason: "Contains D1/D7 retention flags"
    key_fields:
      - user_id
      - retained_d1
      - retained_d7
```

### 8.5 `dag.json`

```json
{
  "nodes": [
    {"id": "acquisition_channel", "type": "pre_treatment_covariate"},
    {"id": "device_type", "type": "pre_treatment_covariate"},
    {"id": "onboarding_v2_exposed", "type": "treatment"},
    {"id": "retained_d7", "type": "outcome"},
    {"id": "user_motivation", "type": "suspected_unobserved_confounder"}
  ],
  "edges": [
    {"from": "acquisition_channel", "to": "onboarding_v2_exposed", "source": "data_suggested", "confidence": "medium"},
    {"from": "acquisition_channel", "to": "retained_d7", "source": "domain_plausible", "confidence": "medium"},
    {"from": "device_type", "to": "retained_d7", "source": "domain_plausible", "confidence": "medium"},
    {"from": "onboarding_v2_exposed", "to": "retained_d7", "source": "causal_question", "confidence": "target_edge"},
    {"from": "user_motivation", "to": "onboarding_v2_exposed", "source": "suspected_unobserved", "confidence": "unknown"},
    {"from": "user_motivation", "to": "retained_d7", "source": "suspected_unobserved", "confidence": "unknown"}
  ]
}
```

---

## 9. Domain Interview Questions

The system should ask targeted questions, not a long generic survey.

### 9.1 Core Questions

Ask these when not already known:

1. What decision are you trying to make?
2. What changed?
3. When did it change?
4. Who was exposed to the change?
5. Who could have been exposed but was not?
6. Was exposure randomized?
7. Was rollout gradual, regional, time-based, user-segmented, or manual?
8. Could users self-select into treatment?
9. What metric moved or should be measured?
10. What else changed around the same time?
11. Which variables existed before the treatment?
12. Which variables are consequences of the treatment?
13. Are there hidden factors that affect both treatment and outcome?
14. Is there any existing experiment assignment table or rollout config?
15. What action will you take depending on the result?

### 9.2 Example Interview Output

```yaml
domain_context:
  treatment_assignment: "not randomized"
  rollout_pattern: "iOS first, then Android"
  simultaneous_changes:
    - "paid marketing campaign increased during same week"
  possible_self_selection: false
  known_post_treatment_variables:
    - tutorial_completed
    - first_purchase_after_signup
  hidden_confounders:
    - user_motivation
```

---

## 10. Method Selection Logic

The method router must select methods based on design.

### 10.1 Method Router Table

| Situation | Recommended Primary Method | Notes |
|---|---|---|
| Proper randomized experiment | A/B test analysis, regression adjustment, CUPED | Highest confidence if implemented correctly |
| Randomized rollout with noncompliance | Instrumental variables, treatment-on-treated, intent-to-treat | Separate assignment from exposure |
| Gradual rollout by date/region/team | Difference-in-differences | Requires pre-trend checks |
| Product launch with aggregate time series only | Interrupted time series | Weak without external control |
| Treated group plus donor pool | Synthetic control | Good for geo/market-level interventions |
| Threshold-based assignment | Regression discontinuity | Requires no manipulation around threshold |
| Observational user-level treatment with rich covariates | Propensity weighting, matching, doubly robust estimation | Requires no unobserved confounding and overlap |
| Heterogeneous effect question | CATE, causal forest, uplift modeling | Requires enough sample size |
| Metric drop/root-cause investigation | Causal graph + root-cause attribution + time-series checks | Often diagnostic, not definitive |
| No control, no pre-period, simultaneous changes | Not identifiable | Recommend future experiment design |

### 10.2 Method Plan Must Include

- Identifiability status.
- Primary method.
- Backup methods.
- Required assumptions.
- Diagnostics.
- Refutation tests.
- Why the method was chosen.
- Why other methods were not chosen.

---

## 11. EDA and Data Audit Requirements

The Data/EDA agent should check:

- Row count and unit count.
- Missing values.
- Duplicate units.
- Treatment assignment rate.
- Outcome rate.
- Timestamp ordering.
- Time coverage.
- Treatment before outcome.
- Covariate availability.
- Covariate missingness.
- Covariate balance.
- Propensity overlap.
- Segment sizes.
- Outliers.
- Seasonality.
- Cohort effects.
- Instrumentation changes.
- Metric definition changes.
- Eligibility consistency.
- Comparison group validity.
- Post-treatment leakage.

### 11.1 Data Readiness Score

Produce a structured readiness summary:

```yaml
data_readiness:
  treatment_available: true
  outcome_available: true
  treatment_time_available: true
  outcome_time_available: true
  pre_treatment_covariates_available: partial
  comparison_group_available: true
  timestamp_order_valid: true
  sample_size_status: medium
  positivity_risk: high
  missingness_risk: medium
  instrumentation_risk: unknown
  pii_risk: low
  overall_status: "usable_with_caution"
```

Allowed statuses:

```text
ready
usable_with_caution
not_ready
not_identifiable
```

---

## 12. SQL and Data Safety Rules

### 12.1 General Rules

- Do not write, update, delete, create, or mutate warehouse data.
- Default to read-only queries.
- Use dry-run/cost estimation when available.
- Use date filters for large event tables.
- Limit samples.
- Aggregate when possible.
- Do not export raw PII.
- Redact or hash user identifiers when possible.
- Store only necessary columns.
- Avoid full table scans unless explicitly approved.
- Ask before running expensive queries.

### 12.2 Causal SQL Correctness Rules

- Define the unit of analysis before joining.
- Avoid many-to-many joins that duplicate units.
- Treatment must be measured before outcome.
- Covariates used for adjustment must be pre-treatment.
- Exclude post-treatment variables from adjustment.
- Define eligibility before treatment assignment.
- Define comparison group carefully.
- Preserve non-treated eligible users.
- Avoid conditioning on colliders.
- Separate assignment from exposure when noncompliance exists.

### 12.3 Query Review Output

```yaml
approved: false
risk_level: high
issues:
  - severity: high
    description: "Query controls for tutorial_completed, which occurs after onboarding exposure."
    suggested_fix: "Remove tutorial_completed from adjustment covariates; treat it as a possible mediator."
  - severity: medium
    description: "No date filter on large event table."
    suggested_fix: "Restrict to rollout window plus pre-period."
```

---

## 13. Estimation and Refutation Modules

### 13.1 Initial Estimation Methods

Implement in this order:

1. A/B test analysis.
2. Regression adjustment.
3. Difference-in-differences.
4. Interrupted time series.
5. Propensity score weighting.
6. Matching.
7. Doubly robust estimation.
8. CATE / causal forest.
9. Synthetic control.
10. Instrumental variables.
11. Regression discontinuity.

### 13.2 Initial Diagnostics

- Covariate balance before/after weighting.
- Propensity overlap.
- Missingness check.
- Timestamp order check.
- Pre-trend check for DiD.
- Placebo outcome.
- Placebo treatment.
- Subset stability.
- Sensitivity to unobserved confounding.

### 13.3 Estimate Output

```json
{
  "effect_size": 0.021,
  "effect_unit": "percentage_points",
  "confidence_interval": [0.008, 0.034],
  "p_value": 0.012,
  "method": "doubly_robust_estimation",
  "estimand": "ATE",
  "sample_size": 128430,
  "treated_units": 42100,
  "control_units": 86330,
  "confidence_level": "medium",
  "interpretation": "Under the stated assumptions, onboarding_v2 likely increased D7 retention by about 2.1 percentage points."
}
```

### 13.4 Robustness Output

```json
{
  "overall_robustness": "medium",
  "checks": [
    {
      "name": "covariate_balance_after_weighting",
      "status": "passed",
      "details": "All standardized mean differences below 0.1 after weighting."
    },
    {
      "name": "propensity_overlap",
      "status": "warning",
      "details": "Poor overlap for paid acquisition users."
    },
    {
      "name": "placebo_outcome",
      "status": "passed",
      "details": "No significant effect on pre-treatment activity proxy."
    }
  ]
}
```

---

## 14. Reporting Requirements

### 14.1 Business Report Structure

`report.md` must include:

1. Executive Summary.
2. Decision Context.
3. Causal Question.
4. Data Used.
5. Method Summary.
6. Main Result.
7. Confidence Level.
8. Assumption Ledger Summary.
9. Robustness and Refutation Checks.
10. Limitations.
11. Recommended Decision.
12. Recommended Next Experiment or Data Collection.

### 14.2 Report Language Rules

Avoid overclaiming.

Bad:

```text
The onboarding flow caused retention to increase.
```

Good:

```text
Under the assumptions shown in the assumption ledger, the estimated effect is +2.1 percentage points. The result is directionally stable across two estimators, but confidence is medium because treatment assignment was not randomized and user motivation may be unobserved.
```

### 14.3 Confidence Levels

Use:

```text
high
medium
low
not_identifiable
```

Definitions:

- **High**: randomized or strong quasi-experimental design, diagnostics pass, assumptions plausible.
- **Medium**: observational or quasi-experimental design with reasonable diagnostics but meaningful assumption risk.
- **Low**: serious confounding, weak comparison group, poor overlap, unstable results.
- **Not identifiable**: available data/design cannot answer the causal question.

### 14.4 Example Executive Summary

```markdown
## Executive Summary

We investigated whether `onboarding_v2` improved D7 retention.

**Conclusion:** Under the current assumptions, onboarding_v2 likely increased D7 retention by approximately **+2.1 percentage points**.

**Confidence:** Medium.

**Why not high confidence:** The rollout was not confirmed randomized. Treated users were overrepresented in paid acquisition channels, and unobserved user motivation may still bias the estimate.

**Recommended decision:** Keep onboarding_v2, but run a 10% randomized holdout for 14 days before declaring final impact.
```

---

## 15. “Not Identifiable” Behavior

The system must treat “not identifiable” as a valid and valuable result.

Example output:

```markdown
## Result: Not Identifiable With Current Data

This question cannot be answered causally from the current data.

Reasons:

1. All users received the feature on the same day.
2. No untreated comparison group exists.
3. There is no sufficiently long pre-period for interrupted time-series analysis.
4. A marketing campaign started on the same day.

Recommended next action:

Create a 10% randomized holdout or use a staggered rollout by region/platform in the next launch.
```

This builds trust and differentiates the product from tools that always produce an answer.

---

## 16. Causal Claim Review Feature

This may become a killer feature.

### 16.1 Use Case

Whenever someone writes:

```text
Feature X increased retention.
```

The system should review the causal claim.

### 16.2 Output

```markdown
## Causal Claim Review

**Claim:** Feature X increased D7 retention.

**Evidence level:** Medium.

**Estimated effect:** +2.1 percentage points.

**Required assumptions:**

- Treatment assignment is ignorable after controlling for channel, country, device, and signup week.
- Treatment happened before D7 outcome measurement.
- No major simultaneous launch caused the same metric movement.

**Main concern:** Treatment assignment was correlated with acquisition channel.

**Recommended wording:**

“Feature X is associated with higher D7 retention, and after adjustment the estimated effect is +2.1 percentage points. However, confidence is medium because rollout was not randomized.”
```

### 16.3 Possible Integrations Later

- Pull request comments.
- Notion docs.
- Slack threads.
- Confluence pages.
- Experiment review docs.
- Launch review templates.

---

## 17. Experiment Design Before Launch

The system should not only analyze after the fact. It should help teams design causal measurement before launch.

### 17.1 PR / Launch Review Example

```markdown
## Causal Risk Review

This change modifies recommendation exposure logic.

Potential outcomes affected:

- CTR
- conversion
- session length
- creator revenue

Suggested measurement design:

- Randomized user-level holdout.
- Stratify by region and platform.
- Minimum 14-day measurement window.
- Pre-register primary metric before launch.

Warning:

If rollout is 100% global, causal effect will be hard to identify after release.
```

This may be one of the strongest adoption wedges because it prevents bad data collection before it happens.

---

## 18. Initial Deterministic Scripts

Implement these scripts inside the Skill first. Later extract into a package/CLI.

### 18.1 `validate_causal_spec.py`

Purpose:

- Validate required fields.
- Check allowed statuses.
- Check treatment/outcome definitions.
- Check that forbidden variables are not also covariates.

CLI:

```bash
python scripts/validate_causal_spec.py analysis/foo/causal_spec.yaml
```

Output:

```json
{
  "valid": false,
  "errors": [
    {
      "field": "variables.pre_treatment_covariates",
      "message": "tutorial_completed appears in forbidden_post_treatment_variables and cannot be used as a pre-treatment covariate."
    }
  ]
}
```

### 18.2 `profile_dataframe.py`

Purpose:

- Profile local CSV/parquet generated from approved queries.
- Compute missingness, cardinality, numeric summaries, binary rates, timestamp ranges.

CLI:

```bash
python scripts/profile_dataframe.py data/analysis.parquet --out artifacts/eda_summary.json
```

### 18.3 `check_timestamps.py`

Purpose:

- Verify treatment time precedes outcome time.
- Identify invalid rows.
- Check covariate timestamp availability if possible.

CLI:

```bash
python scripts/check_timestamps.py data/analysis.parquet \
  --treatment-time onboarding_started_at \
  --outcome-time d7_window_end_at \
  --out artifacts/timestamp_check.json
```

### 18.4 `check_balance.py`

Purpose:

- Compare treated/control covariates.
- Compute standardized mean differences.
- Generate balance summary.

CLI:

```bash
python scripts/check_balance.py data/analysis.parquet \
  --treatment onboarding_v2_exposed \
  --covariates country,device_type,acquisition_channel,signup_week \
  --out artifacts/balance_check.json
```

### 18.5 `suggest_method.py`

Purpose:

- Read causal spec and data readiness.
- Produce `method_plan.json`.

CLI:

```bash
python scripts/suggest_method.py analysis/foo/causal_spec.yaml \
  --data-readiness artifacts/data_readiness.json \
  --out method_plan.json
```

### 18.6 `generate_report.py`

Purpose:

- Render report from artifacts.
- Keep initial version template-based.

CLI:

```bash
python scripts/generate_report.py analysis/foo \
  --out report.md \
  --technical-out technical_appendix.md
```

---

## 19. Future Standalone CLI Design

Once scripts stabilize, package them into a CLI named `causal`.

### 19.1 Basic Commands

```bash
causal init onboarding_retention
causal ask "Did onboarding_v2 improve D7 retention?"
causal spec validate causal_spec.yaml
causal profile data.parquet
causal timestamps check data.parquet
causal balance check data.parquet --treatment onboarding_v2_exposed
causal method suggest
causal estimate --method doubly_robust
causal refute --all
causal report
```

### 19.2 Warehouse Commands

```bash
causal connect bigquery --project my-project --dataset analytics
causal schema search "onboarding retention signup experiment"
causal schema describe analytics.onboarding_events
causal sql dry-run queries/population.sql
causal sql run queries/population.sql --destination artifacts/population.parquet
```

### 19.3 Agent-friendly Commands

```bash
causal ask "Did the March onboarding rollout improve D7 retention?" \
  --agent-mode supervised \
  --warehouse bigquery \
  --max-cost-usd 5 \
  --pii-policy strict
```

### 19.4 Adapter Philosophy

Standalone CLI should eventually support multiple agent systems, but not depend on any one of them.

```text
Claude Code Skill uses CLI.
Codex can use CLI.
Cursor Agent can use CLI.
CI can use CLI.
Internal company agents can use CLI.
```

---

## 20. Testing Strategy

### 20.1 Unit Tests

Test deterministic scripts:

- `validate_causal_spec.py`
- `profile_dataframe.py`
- `check_timestamps.py`
- `check_balance.py`
- `suggest_method.py`
- `generate_report.py`

### 20.2 Golden Scenario Tests

Create synthetic scenarios:

1. Randomized A/B test with known positive effect.
2. Observational confounding where naive correlation is wrong.
3. Difference-in-differences with parallel trends.
4. Difference-in-differences with violated pre-trends.
5. No comparison group → not identifiable.
6. Post-treatment leakage variable included → validation failure.
7. Poor propensity overlap → warning.
8. Simultaneous launch → confidence downgrade.

### 20.3 Agent Workflow Tests

Create prompt fixtures for Claude Code Skill:

```text
Investigate whether onboarding_v2 improved D7 retention.
```

Expected artifacts:

- `causal_spec.yaml` exists.
- `assumption_ledger.yaml` exists.
- `method_plan.json` exists.
- `report.md` contains confidence level.
- Report does not overclaim.
- Post-treatment variable is not controlled.

### 20.4 Report Quality Tests

Automatically check reports for forbidden overclaims:

Bad phrases:

```text
proved that
definitely caused
guaranteed impact
caused retention to increase
```

Unless high-confidence randomized design is present, require softer language:

```text
under the stated assumptions
estimated effect
likely
consistent with
confidence is medium/low
```

---

## 21. MVP Scope

### 21.1 MVP Must Have

- Claude Code Skill folder.
- Subagent definitions.
- Causal spec template.
- Assumption ledger template.
- Method router reference.
- SQL safety rules.
- Report template.
- At least three deterministic scripts:
  - `validate_causal_spec.py`
  - `check_balance.py`
  - `suggest_method.py`
- Example analysis folder.
- README with usage examples.

### 21.2 MVP Should Support

- Feature launch impact.
- A/B test sanity check.
- Observational treatment with pre-treatment covariates.
- Not identifiable result.
- Experiment design recommendation.

### 21.3 MVP Can Defer

- Full causal discovery.
- Complex DAG editor.
- Hosted web UI.
- Full DoWhy/EconML integration.
- Snowflake/Redshift connectors.
- Automated dashboard integration.
- Real-time Slack/PR bots.

---

## 22. Phase-by-phase Roadmap

### Phase 1 — Claude Code Skill MVP

Goal: validate workflow and adoption.

Build:

- Skill instructions.
- Subagents.
- Templates.
- Method-router reference.
- Report generator prompt/template.
- Manual or semi-manual data-source discovery.

Output:

- `causal_spec.yaml`
- `assumption_ledger.yaml`
- `method_plan.json`
- `report.md`
- `technical_appendix.md`

### Phase 2 — Script-backed Skill

Goal: make core checks deterministic.

Build:

- Spec validation.
- Data profiling.
- Timestamp check.
- Balance check.
- Method suggestion.
- Report rendering.

### Phase 3 — Estimation Modules

Goal: produce actual causal estimates.

Build:

- A/B test analysis.
- Difference-in-differences.
- Propensity weighting.
- Doubly robust estimation.
- Placebo tests.
- Sensitivity checks.

### Phase 4 — Standalone CLI Extraction

Goal: portability and reproducibility.

Build:

- `causal init`
- `causal spec validate`
- `causal profile`
- `causal method suggest`
- `causal estimate`
- `causal report`

### Phase 5 — Integrations

Goal: broader distribution.

Build:

- Claude Code Skill powered by CLI.
- Codex usage guide.
- Cursor/other agent usage guide.
- GitHub Action for causal claim review.
- BigQuery connector.
- dbt metadata integration.

---

## 23. Key Risks and Mitigations

### 23.1 LLM-generated DAG hallucination

Mitigation:

- Separate user-confirmed, data-suggested, and LLM-suggested edges.
- Use an assumption ledger.
- Never treat DAG as truth.

### 23.2 Overclaiming causality

Mitigation:

- Confidence levels.
- Report language rules.
- “Not identifiable” output.
- Required assumptions before causal claims.

### 23.3 Post-treatment control mistakes

Mitigation:

- Explicit forbidden post-treatment variables.
- Timestamp checks.
- SQL safety reviewer.
- Spec validation.

### 23.4 Expensive or unsafe warehouse queries

Mitigation:

- Dry-run/cost checks.
- Date filters.
- Sampling.
- Approval before expensive queries.
- Read-only query policy.

### 23.5 Data leakage / PII

Mitigation:

- PII policy.
- Redaction/hashing.
- Aggregation.
- Local-only artifacts.
- Avoid raw user-level exports unless approved.

### 23.6 Weak adoption

Mitigation:

- Start inside Claude Code.
- Focus on product analytics wedge.
- Produce reports users can immediately share.
- Add PR/launch review use case.

---

## 24. What Makes This Better Than Existing Causal Agent Demos

This system should improve on graph-first causal agent demos by being:

1. **Decision-first**, not graph-first.
2. **Treatment-effect-first**, not causal-discovery-first.
3. **Workflow-native**, not upload-based.
4. **Agent-native**, especially inside Claude Code.
5. **Artifact-driven**, not chat-only.
6. **Conservative about identifiability**.
7. **Explicit about assumptions**.
8. **Useful before launch**, not only after data is collected.
9. **Integrated with real data environments**.
10. **Portable toward a standalone CLI**.

---

## 25. First Build Tasks for AI Coding Agent

### Task 1: Create Project Skeleton

Create:

```text
.claude/skills/causal-decision-debugger/
.claude/agents/
examples/onboarding_retention/
scripts/
tests/
```

### Task 2: Create Skill and Agent Markdown Files

Implement:

- `SKILL.md`
- `data-scout.md`
- `sql-safety-reviewer.md`
- `causal-methodologist.md`
- `assumption-ledger-agent.md`
- `report-writer.md`

### Task 3: Create Templates

Implement:

- `templates/causal_spec.yaml`
- `templates/assumption_ledger.yaml`
- `templates/method_plan.json`
- `templates/report.md`
- `templates/technical_appendix.md`

### Task 4: Create Reference Docs

Implement:

- `reference/method-router.md`
- `reference/assumption-ledger.md`
- `reference/sql-safety-rules.md`
- `reference/causal-spec-schema.md`
- `reference/report-template.md`
- `reference/causal-glossary.md`

### Task 5: Implement Deterministic Scripts

Implement:

- `scripts/validate_causal_spec.py`
- `scripts/profile_dataframe.py`
- `scripts/check_timestamps.py`
- `scripts/check_balance.py`
- `scripts/suggest_method.py`
- `scripts/generate_report.py`

Use Python.

Recommended dependencies:

```text
pandas
pyyaml
numpy
scipy
scikit-learn
statsmodels
jinja2
pytest
```

Optional later:

```text
dowhy
econml
causalml
causal-learn
polars
duckdb
```

### Task 6: Add Example Scenario

Create example files under:

```text
examples/onboarding_retention/
```

Include:

- sample `causal_spec.yaml`
- sample `assumption_ledger.yaml`
- sample `method_plan.json`
- sample `report.md`
- synthetic data generation script
- example test run

### Task 7: Add Tests

Implement pytest tests for:

- valid and invalid causal specs.
- post-treatment variable validation.
- balance checking.
- method suggestion.
- not-identifiable cases.
- report generation.

### Task 8: Add README

README should explain:

- What the system does.
- How to install/use inside Claude Code.
- Example prompts.
- Artifact structure.
- Safety rules.
- Roadmap.

---

## 26. Example User-facing README Snippet

```markdown
# Causal Decision Debugger

A Claude Code Skill for investigating whether business/product changes caused metric changes.

## Example

In Claude Code, ask:

> Use the causal decision debugger to investigate whether onboarding_v2 improved D7 retention. Use BigQuery if available. Do not export PII. Keep query cost low. Generate a business report and technical appendix.

The Skill will create:

- `analysis/<id>/causal_spec.yaml`
- `analysis/<id>/assumption_ledger.yaml`
- `analysis/<id>/method_plan.json`
- `analysis/<id>/report.md`
- `analysis/<id>/technical_appendix.md`

## Core principles

- Decision-first, not graph-first.
- Conservative causal claims.
- Explicit assumptions.
- Reproducible artifacts.
- Safe data access.
- “Not identifiable” is a valid answer.
```

---

## 27. Final Product North Star

The product should help teams answer:

1. Can we actually know whether X caused Y?
2. What evidence do we have?
3. What assumptions are required?
4. What method is appropriate?
5. How big is the effect?
6. How robust is the conclusion?
7. What decision should we make?
8. What experiment should we run next?

The system wins if it changes team behavior from:

```text
The dashboard moved, so our launch worked.
```

to:

```text
The estimated effect is positive under these assumptions, robustness is medium, and the main remaining risk is non-random treatment assignment. We should keep the feature but run a holdout before declaring final impact.
```

That is the product.

