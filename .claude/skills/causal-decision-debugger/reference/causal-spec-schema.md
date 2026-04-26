# Causal Spec Schema

The canonical structure of `causal_spec.yaml` is defined by `src/causal_debugger/schemas/causal_spec.schema.json`. Validate any spec via:

```bash
uv run python -m causal_debugger.spec.validate path/to/causal_spec.yaml
```

Or the script shim:

```bash
uv run python .claude/skills/causal-decision-debugger/scripts/validate_causal_spec.py path/to/causal_spec.yaml
```

## Required top-level keys

- `analysis_id`
- `status` (`draft | in_progress | ready | completed | archived`)
- `business_decision` (`question` is required)
- `causal_question` (`question`, `unit`, `treatment`, `outcome`, `comparison_group`)
- `population` (`eligibility_definition`)
- `variables` (`pre_treatment_covariates`, `forbidden_post_treatment_variables`)
- `assumptions` (mapping of name → object with `status`)

## Cross-field rule (validator)

The `validate_causal_spec.py` script also enforces:

- No variable appears in both `pre_treatment_covariates` and `forbidden_post_treatment_variables`.
- Every `assumptions[*].status` is in the allowed enum.
- `methods.primary` (when set) corresponds to a known method name in `reference/method-router.md`.
