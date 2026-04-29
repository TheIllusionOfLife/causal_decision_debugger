# Causal Decision Debugger

A Claude Code Skill plus Python toolkit that helps teams move from correlation-based claims to decision-grade causal evidence. It translates business questions into causal questions, audits the data, picks an appropriate identification strategy, runs estimation and refutation checks, and writes a business-readable report. "Not identifiable" is a valid (and valuable) answer.

## What you get

- **Claude Code plugin** (`skills/causal-decision-debugger/` + `agents/`) with subagents for data discovery, SQL safety review, methodology, assumption ledgering, and report writing.
- **Deterministic Python scripts** for spec validation, EDA, timestamp checks, covariate balance, method routing, and report rendering.
- **Causal estimators** covering A/B test analysis, difference-in-differences, interrupted time series, propensity weighting, matching, doubly robust estimation, CATE/causal forests, synthetic control, instrumental variables, and regression discontinuity.
- **Refutation suite** including placebo tests, subset stability, and sensitivity to unobserved confounding.
- **End-to-end example** under `examples/onboarding_retention/` that runs the full pipeline on synthetic data.

## Install (Claude Code plugin)

In Claude Code:

```text
/plugin marketplace add github:TheIllusionOfLife/causal_decision_debugger
/plugin install causal-decision-debugger
```

The plugin bundles the `causal_debugger` Python wheel under `skills/causal-decision-debugger/vendor/`. On first invocation, Claude will run a stdlib-only `bootstrap.py` that installs the wheel via `uv tool install`, `pipx`, or `pip --user` (whichever is available).

**Network required on first run.** The bundled wheel is `causal_debugger` itself; transitive dependencies (`pandas`, `scipy`, `scikit-learn`, `statsmodels`, `linearmodels`, `dowhy`, `econml`, `pyyaml`, `jinja2`, `jsonschema`, `pyarrow`) still resolve from PyPI on first install. Subsequent runs are fully offline. Python 3.11+.

## Use it inside Claude Code

After install, ask Claude:

> Use the causal decision debugger to investigate whether onboarding_v2 improved D7 retention. Do not export PII. Generate a business report and technical appendix.

The Skill will produce:

- `analysis/<id>/causal_spec.yaml`
- `analysis/<id>/assumption_ledger.yaml`
- `analysis/<id>/method_plan.json`
- `analysis/<id>/report.md`
- `analysis/<id>/technical_appendix.md`

## Run the example pipeline

```bash
causal-debugger pipeline examples/onboarding_retention
```

This validates the spec, runs balance and timestamp checks, picks a method, estimates the effect, runs refutation, and renders `report.md`. If `data/` is missing under the example, regenerate it via `uv run python examples/onboarding_retention/generate_synthetic.py` (the script imports `causal_debugger`, so a bare `python` from outside a `uv sync` checkout will not find it; from a plugin-only install, run `causal-debugger doctor` and use the reported `python_executable`).

## Develop

```bash
uv sync --extra dev    # set up dev environment
uv run pytest          # full test suite
uv run ruff check .    # lint
uv build               # build the wheel into dist/
```

When developing in this repo, the `.claude/skills/` and `.claude/agents/` symlinks (gitignored) point at the top-level `skills/` and `agents/` so Claude Code finds the assets. Re-run `uv build && cp dist/*.whl skills/causal-decision-debugger/vendor/` after changes to the Python package, and regenerate `vendor/manifest.json` (CI's manifest check will fail otherwise).

## Repository layout

```text
.claude-plugin/                            plugin.json + marketplace.json
skills/causal-decision-debugger/           SKILL.md, reference docs, templates, vendored wheel, bootstrap.py
agents/                                    Subagent definitions (5 agents)
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
