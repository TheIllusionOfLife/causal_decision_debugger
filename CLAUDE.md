# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Dependencies are managed by `uv` (Python 3.11+). The package targets a wheel built from `src/causal_debugger`.

```bash
uv sync --extra dev                          # install runtime + dev deps
uv run pytest                                # full test suite
uv run pytest tests/methods/test_did.py::test_did_recovers_known_effect  # single test
uv run pytest --cov                          # coverage (config in pyproject.toml)
uv run ruff check .                          # lint (excludes analysis/ and .venv)
uv run ruff format .                         # formatter (double quotes, line-length 100)
```

Run the end-to-end pipeline against the bundled example:

```bash
# After bootstrap (or `uv sync --extra dev` for in-tree dev):
causal-debugger pipeline examples/onboarding_retention
# Equivalently, from a uv-synced checkout:
uv run python -m causal_debugger.pipeline examples/onboarding_retention
```

The pipeline expects an analysis directory containing `causal_spec.yaml` (and optionally `assumption_ledger.yaml`); it writes artifacts into `<analysis_dir>/artifacts/` plus `method_plan.json` and `report.md` at the root.

The example's `data/` is gitignored. Regenerate it before running the pipeline if missing:

```bash
uv run python examples/onboarding_retention/generate_synthetic.py
```

After modifying `src/causal_debugger/`, rebuild the bundled wheel and refresh its manifest so the install-test CI does not fail:

```bash
uv build
cp dist/causal_debugger-*.whl skills/diagnose/vendor/
# regenerate sha256 + metadata_sha256 in skills/diagnose/vendor/manifest.json
```

### Develop the plugin in-tree

Two ways to load the plugin during development:

- **Symlinks** (already wired up): `.claude/skills/diagnose -> ../../skills/diagnose` and `.claude/agents -> ../agents`. Both gitignored. Claude Code finds the plugin assets when launched from the repo root.
- **`--plugin-dir` flag**: `claude --plugin-dir .` from the repo root. Doesn't require symlinks.

After editing `SKILL.md`, an agent file, or `.claude-plugin/plugin.json`, run `/reload-plugins` inside Claude Code to pick up changes without restarting.

## Architecture

The repo is a **Claude Code plugin** that bundles **two surfaces over the same core**:

1. **Plugin assets at the repo root**: `.claude-plugin/{plugin,marketplace}.json`, `skills/diagnose/` (SKILL.md + reference + templates + scripts/bootstrap.py + scripts/_install_paths.py + vendor/wheel), `agents/` (`data-scout`, `sql-safety-reviewer`, `causal-methodologist`, `assumption-ledger-agent`, `report-writer`), and `bin/causal-debugger` (a stdlib-only Python shim that Claude Code auto-PATHs while the plugin is enabled — it dispatches into the venv). The Skill is the user-facing workflow; Claude reads SKILL.md and dispatches to subagents and the `causal-debugger` CLI. Local symlinks under `.claude/skills/diagnose` and `.claude/agents` (gitignored) point at the top-level dirs so Claude Code finds them when working in this repo.
2. **`causal_debugger` Python package** at `src/causal_debugger/` containing the deterministic logic, exposed as the `causal-debugger` console script (entry point in `cli.py`). The skill's `scripts/bootstrap.py` installs the bundled wheel into a per-plugin venv at `${CLAUDE_PLUGIN_DATA}/venv/` (the persistent data dir documented in the Claude Code plugins reference) so heavy transitive deps (`pandas`, `scipy`, `dowhy`, `econml`) live in the venv and survive plugin updates without polluting the user's Python. `bin/causal-debugger` is a thin shim that resolves the data dir via the shared `_install_paths` helper and `subprocess.call`s into `${CLAUDE_PLUGIN_DATA}/venv/bin/causal-debugger`. If the venv is missing, the shim prints a "run bootstrap" message instead of silently dispatching to a different CLI on PATH.

### Pipeline shape (src/causal_debugger/pipeline.py)

`run(analysis_dir)` is the orchestrator. The flow is **validate → audit → route → estimate → refute → render**:

1. Loads + validates `causal_spec.yaml` against the bundled `causal_spec` schema (`spec/validate.py`).
2. Reads the data table from `spec.data.local_path` (`data/io.py`).
3. Audits: `data/profile.py` (always), `data/timestamps.py` (only when treatment_time + outcome_window columns exist), `data/balance.py` (SMD; only when treatment + covariates are present).
4. Routes to a method via `methods/router.py` based on a `RouterContext` derived from the spec (`context_from_spec`). The router can return `identifiability_status: "not_identifiable"`, in which case the pipeline writes `identifiability_failure.json` and a report explaining why, then exits without estimating. **This is a valid outcome and must be preserved.**
5. Dispatches to one of ten estimators in `methods/` (`ab_test`, `did`, `its`, `synthetic_control`, `ipw`, `matching`, `doubly_robust`, `cate`, `iv`, `rdd`). The dispatch table is built in `_make_dispatch` and reads design column names from `spec.data.columns` with defaults in `_DEFAULT_DESIGN_COLUMNS` (e.g. `group`, `post`, `period`, `unit_id`, `instrument`, `running`, `treated_unit`, `rdd_cutoff`).
6. Refutes via `refutation/placebo.py` (treatment permutation), `refutation/subset.py` (segment stability on the first low-cardinality covariate), and `refutation/sensitivity.py` (E-value-style unobserved confounding bound). The placebo and subset estimators reuse the primary estimator and fall back to A/B diff-in-means if the segment lacks required columns.
7. Renders `report.md` via `reporting/render.py` (Jinja2 template at `templates/report.md`).

### Contract artifacts

Every artifact has a JSON schema under `src/causal_debugger/schemas/` (force-included into the wheel via `pyproject.toml`):

- `causal_spec.schema.json`, `assumption_ledger.schema.json` — inputs.
- `estimate_result.schema.json`, `refutation_result.schema.json`, `identifiability_failure.schema.json` — outputs from estimators / refutation / the not-identifiable branch.

`tests/contracts/test_schemas.py` and `test_templates.py` enforce that artifacts and the YAML/JSON templates under `skills/diagnose/templates/` validate. **When you add an estimator or refutation check, return a payload that matches the corresponding schema and add a contract test.**

JSON dumps in the pipeline use `allow_nan=False` deliberately so estimator NaN/Inf leaks fail loudly instead of producing invalid JSON.

### Method router (methods/router.py)

`suggest_method` is a pure function over `RouterContext` (randomized, has_pre_period, rollout_pattern, threshold_assignment, has_donor_pool, has_instrument, etc.). It returns `{primary_method, secondary_methods, required_assumptions, diagnostics, refutation_tests, identifiability_status, reasoning_summary}`. The order of branches encodes priority — randomized first, then RD, then DiD/staggered, etc. Tests in `tests/methods/test_router.py` pin behavior; treat the routing logic as a contract.

### Tests

`tests/` mirrors `src/`. `tests/scenarios/` exercises end-to-end DGPs from `src/causal_debugger/scenarios/dgps.py` (synthetic data generators with known ground truth) — these are the integration tests for estimator correctness.

## Project conventions

- **No PII export, read-only data access, dry-run before expensive queries.** These are core principles for the Skill and any new tooling.
- **"Not identifiable" is a first-class output.** Don't paper over missing comparison groups or pre-periods with weaker estimators; surface the gap in the report.
- **Never control for post-treatment variables.** Pre-treatment covariates are tracked in the spec (`variables.pre_treatment_covariates`); post-treatment fields are forbidden by the schema and must stay that way.
- Upper bounds on `scipy` (<1.16) and `scikit-learn` (<1.7) in `pyproject.toml` are forced by `dowhy` and `econml` pins. Don't bump without verifying the upstream constraint has been relaxed.
