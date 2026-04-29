# Causal Decision Debugger

A Claude Code Skill plus Python toolkit that helps teams move from correlation-based claims to decision-grade causal evidence. It translates business questions into causal questions, audits the data, picks an appropriate identification strategy, runs estimation and refutation checks, and writes a business-readable report. "Not identifiable" is a valid (and valuable) answer.

## What you get

- **Claude Code plugin** (`skills/diagnose/` + `agents/`) with subagents for data discovery, SQL safety review, methodology, assumption ledgering, and report writing.
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

The plugin bundles the `causal_debugger` Python wheel under `skills/diagnose/vendor/`. On first invocation, Claude will run a stdlib-only `bootstrap.py` that creates an isolated virtualenv at `${CLAUDE_PLUGIN_DATA}/venv/` (the per-plugin persistent data dir) and `pip install`s the bundled wheel into it. Inside Claude Code, the plugin's `bin/causal-debugger` shim is auto-on-PATH and dispatches into the venv. Outside Claude Code, invoke the venv's binary directly (`~/.claude/plugins/data/causal-decision-debugger*/venv/bin/causal-debugger`) or add it to your shell PATH.

**Network required on first run.** The bundled wheel is `causal_debugger` itself; transitive dependencies (`pandas`, `scipy`, `scikit-learn`, `statsmodels`, `linearmodels`, `dowhy`, `econml`, `pyyaml`, `jinja2`, `jsonschema`, `pyarrow`) still resolve from PyPI on first install. The first install downloads ~500 MB and takes 5-30 minutes; subsequent runs are instant. Python 3.11+.

**Windows note.** The `bin/causal-debugger` shim relies on a Unix-style shebang and executable bit. On Windows the venv is still created (under `${CLAUDE_PLUGIN_DATA}\venv\Scripts\`), but if the bin/ shim doesn't auto-resolve via Claude Code's Bash tool, invoke `python skills/diagnose/scripts/bootstrap.py` and then call the venv's `causal-debugger.exe` directly.

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

Two ways to load the plugin during development:

- **Symlinks** (already wired up in this repo): `.claude/skills/diagnose -> ../../skills/diagnose` and `.claude/agents -> ../agents`. Both are gitignored. Claude Code picks them up when you launch from this directory.
- **`--plugin-dir` flag**: `claude --plugin-dir .` from the repo root. Doesn't require symlinks — useful for one-off testing in a clean directory.

After editing `SKILL.md`, an agent file, or the manifest, run `/reload-plugins` inside Claude Code to pick up changes without restarting.

After modifying `src/causal_debugger/`, rebuild the bundled wheel and refresh its manifest so the install-test CI does not fail:

```bash
uv build
cp dist/causal_debugger-*.whl skills/diagnose/vendor/
# Regenerate sha256 + metadata_sha256 in skills/diagnose/vendor/manifest.json
```

## Release

To publish the plugin to the official Anthropic marketplace, submit it via [`https://claude.ai/settings/plugins/submit`](https://claude.ai/settings/plugins/submit). The marketplace entry already lives in `.claude-plugin/marketplace.json`; tag a release with `claude plugin tag --push` (see [Plugins reference](https://code.claude.com/docs/plugins-reference#plugin-tag)).

## Repository layout

```text
.claude-plugin/                            plugin.json + marketplace.json
skills/diagnose/                           SKILL.md, reference docs, templates, vendored wheel, bootstrap.py, _install_paths.py
agents/                                    Subagent definitions (5 agents)
bin/causal-debugger                        Plugin shim (auto-on-PATH inside Claude Code) that dispatches into the venv
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
