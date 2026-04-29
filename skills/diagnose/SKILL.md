---
name: Causal Decision Debugger
description: Use this when the user asks whether a product, business, marketing, pricing, ranking, onboarding, marketplace, policy, or engineering change caused a metric change. Helps translate business questions into causal specs, inspect data, select causal inference methods, run checks, and generate decision-grade reports.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Causal Decision Debugger

## Goal

Help users move from correlation-based claims to careful causal claims with explicit assumptions, data checks, estimates, robustness checks, and recommended next actions.

## Setup (first run only)

The skill ships a bundled Python wheel. Before running any deterministic script, ask the user for permission to bootstrap, then execute:

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/diagnose/scripts/bootstrap.py
```

Bootstrap is idempotent (skips if the bundled wheel's metadata fingerprint already matches the installed venv) and stdlib-only. It creates an isolated virtualenv at `${CLAUDE_PLUGIN_DATA}/venv/` and `pip install`s the bundled wheel into it. **Network access is required on the first run** to resolve heavy transitive dependencies (`pandas`, `scipy`, `scikit-learn`, `dowhy`, `econml`) from PyPI; the bundled wheel only contains `causal_debugger` itself. The first install downloads ~500 MB and takes 5-30 minutes; subsequent runs are instant.

After success, the `causal-debugger` CLI is auto-on-PATH inside Claude Code via the plugin's `bin/` directory. Outside Claude Code, invoke it directly at `${CLAUDE_PLUGIN_DATA}/venv/bin/causal-debugger`.

## Required workflow

1. Clarify the decision and causal question.
2. Create or update `causal_spec.yaml` and validate it via `causal-debugger validate-spec <path>`.
3. Identify unit, treatment, outcome, treatment time, outcome window, and comparison group.
4. Inspect available data through existing project tools.
5. Check timestamp order and leakage risk via `causal-debugger check-timestamps`.
6. Identify pre-treatment covariates and forbidden post-treatment variables.
7. Build `assumption_ledger.yaml` (its schema is enforced by the same CLI).
8. Select a method via `causal-debugger suggest-method` and write `method_plan.json`.
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

Delegate to these subagents (bundled with the plugin under `agents/`):

- `data-scout` — find candidate data sources.
- `sql-safety-reviewer` — review SQL for safety and causal correctness.
- `causal-methodologist` — pick an identification strategy.
- `assumption-ledger-agent` — maintain the assumption ledger.
- `report-writer` — author the business report and appendix.

## Deterministic CLI

After bootstrap, invoke via the `causal-debugger` console script (CWD-independent):

- `causal-debugger validate-spec <causal_spec.yaml>` — schema validation + cross-field rules.
- `causal-debugger profile <data.parquet>` — missingness, cardinality, timestamp ranges.
- `causal-debugger check-timestamps <data.parquet>` — confirms treatment time precedes outcome time.
- `causal-debugger check-balance <data.parquet>` — covariate balance / SMD.
- `causal-debugger suggest-method <causal_spec.yaml>` — method routing per spec §10.
- `causal-debugger report <analysis_dir>` — render `report.md` from artifacts.
- `causal-debugger pipeline <analysis_dir>` — full orchestration.
- `causal-debugger doctor` — environment diagnostics for bug reports.

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
