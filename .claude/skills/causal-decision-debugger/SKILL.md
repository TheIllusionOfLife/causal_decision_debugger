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
2. Create or update `causal_spec.yaml` (must validate against `src/causal_debugger/schemas/causal_spec.schema.json`).
3. Identify unit, treatment, outcome, treatment time, outcome window, and comparison group.
4. Inspect available data through existing project tools.
5. Check timestamp order and leakage risk.
6. Identify pre-treatment covariates and forbidden post-treatment variables.
7. Build `assumption_ledger.yaml` (validates against `src/causal_debugger/schemas/assumption_ledger.schema.json`).
8. Select a method and write `method_plan.json`.
9. Generate safe SQL drafts when needed; route via the `sql-safety-reviewer` agent.
10. Ask the user before running expensive or risky queries.
11. Run EDA, balance checks, estimation, and robustness checks where possible.
12. Produce `report.md` and `technical_appendix.md`.

## Behavioral rules

- Be decision-first, not graph-first.
- Be conservative with causal claims.
- Never claim causality without assumptions.
- Explicitly say "not identifiable" when the data cannot answer the question.
- Separate confirmed facts, user-provided assumptions, data-suggested patterns, and model/LLM-suggested hypotheses.
- Never control for post-treatment variables.
- Always check timestamp order.
- Always warn about unobserved confounding when relevant.
- Prefer reproducible artifacts over one-off chat answers.
- Avoid exporting PII.
- Prefer aggregated or sampled data for exploration.
- Use dry runs or cost checks before warehouse queries when available.

## Subagents

Delegate to these subagents (defined under `.claude/agents/`):

- `data-scout` — find candidate data sources.
- `sql-safety-reviewer` — review SQL for safety and causal correctness.
- `causal-methodologist` — pick an identification strategy.
- `assumption-ledger-agent` — maintain the assumption ledger.
- `report-writer` — author the business report and appendix.

## Deterministic scripts

Invoke via `uv run python -m causal_debugger.<module> ...` (CWD-independent). Convenience shims live in `.claude/skills/causal-decision-debugger/scripts/`:

- `validate_causal_spec.py` — schema validation + cross-field rules.
- `profile_dataframe.py` — missingness, cardinality, timestamp ranges.
- `check_timestamps.py` — confirms treatment time precedes outcome time.
- `check_balance.py` — covariate balance / SMD.
- `suggest_method.py` — method routing per spec §10.
- `generate_report.py` — render `report.md` from artifacts.
- `run_pipeline.py` — full orchestration.

## Output artifacts

Place artifacts under `analysis/<analysis_id>/`. Required:

- `causal_spec.yaml`
- `assumption_ledger.yaml`
- `data_sources.yaml`
- `method_plan.json`
- `report.md`
- `technical_appendix.md`

Optional:

- `dag.json`
- `queries/*.sql`
- `artifacts/eda_summary.json`
- `artifacts/balance_check.json`
- `artifacts/timestamp_check.json`
- `artifacts/estimates.json` (validates against `estimate_result.schema.json`)
- `artifacts/robustness.json` (each entry validates against `refutation_result.schema.json`)

When a method cannot be applied, write `artifacts/identifiability_failure.json` (validates against `identifiability_failure.schema.json`) and call out the result in the report.

## Reference docs

- `reference/method-router.md` — situation → method table.
- `reference/sql-safety-rules.md` — SQL correctness and safety rules.
- `reference/assumption-ledger.md` — guidance for ledger entries.
- `reference/causal-spec-schema.md` — pointer to the JSON schema and field meanings.
- `reference/report-template.md` — required sections + language rules.
- `reference/causal-glossary.md` — vocabulary aligned with the spec.
