# Causal Decision Debugger

A Claude Code Skill plus Python toolkit that helps teams move from correlation-based claims to decision-grade causal evidence. It translates business questions into causal questions, audits the data, picks an appropriate identification strategy, runs estimation and refutation checks, and writes a business-readable report. "Not identifiable" is a valid (and valuable) answer.

## What you get

- **Claude Code Skill** under `.claude/skills/causal-decision-debugger/` with subagents for data discovery, SQL safety review, methodology, assumption ledgering, and report writing.
- **Deterministic Python scripts** for spec validation, EDA, timestamp checks, covariate balance, method routing, and report rendering.
- **Causal estimators** covering A/B test analysis, difference-in-differences, interrupted time series, propensity weighting, matching, doubly robust estimation, CATE/causal forests, synthetic control, instrumental variables, and regression discontinuity.
- **Refutation suite** including placebo tests, subset stability, and sensitivity to unobserved confounding.
- **End-to-end example** under `examples/onboarding_retention/` that runs the full pipeline on synthetic data.

## Install

```bash
uv sync --extra dev
```

The package targets Python 3.11+. `uv` resolves and installs `pandas`, `numpy`, `scipy`, `scikit-learn`, `statsmodels`, `linearmodels`, `dowhy`, `econml`, `pyyaml`, `jinja2`, and `jsonschema`.

## Use it inside Claude Code

In a project that has this repo's `.claude/` copied into it, ask:

> Use the causal decision debugger to investigate whether onboarding_v2 improved D7 retention. Do not export PII. Generate a business report and technical appendix.

The Skill will produce:

- `analysis/<id>/causal_spec.yaml`
- `analysis/<id>/assumption_ledger.yaml`
- `analysis/<id>/method_plan.json`
- `analysis/<id>/report.md`
- `analysis/<id>/technical_appendix.md`

## Run the example pipeline

```bash
uv run python .claude/skills/causal-decision-debugger/scripts/run_pipeline.py \
    examples/onboarding_retention
```

This regenerates synthetic data, validates the spec, runs balance and timestamp checks, picks a method, estimates the effect, runs refutation, and renders `report.md`.

## Repository layout

```
.claude/skills/causal-decision-debugger/   Skill markdown, references, templates, script shims
.claude/agents/                            Subagent definitions
src/causal_debugger/                       Importable package backing the scripts
  schemas/                                 JSON schemas for artifacts
  spec/                                    Spec validation
  data/                                    Profile, timestamps, balance
  methods/                                 Router + estimators
  refutation/                              Placebo, subset, sensitivity
  reporting/                               Jinja2 report rendering
examples/onboarding_retention/             End-to-end example
tests/                                     pytest tree mirroring src/
```

## Core principles

- **Decision-first**, not graph-first.
- **Conservative** about identifiability. "Not identifiable" is a valid result.
- **Explicit assumptions** tracked in an assumption ledger.
- **Reproducible artifacts** beat one-off chat answers.
- **Safe data access**: read-only, no PII export, dry-run before expensive queries.

## Roadmap

- Phase 4: Standalone `causal` CLI extracted from the package.
- Phase 5: Warehouse connectors (BigQuery dry-run first), GitHub Action for causal claim review, PR/launch design helper.

See [`causal_decision_debugger_build_spec.md`](./causal_decision_debugger_build_spec.md) for the full design specification.
