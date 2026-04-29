# Causal Spec Schema

The canonical structure of `causal_spec.yaml` is defined by the `causal_spec` JSON schema bundled inside the `causal_debugger` Python package. Validate any spec via the bundled CLI:

```bash
causal-debugger validate-spec path/to/causal_spec.yaml
```

If the CLI is not yet on `$PATH`, run the bootstrap first:

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/diagnose/scripts/bootstrap.py
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

`causal-debugger validate-spec` also enforces:

- No variable appears in both `pre_treatment_covariates` and `forbidden_post_treatment_variables`.
- Every `assumptions[*].status` is in the allowed enum.
- `methods.primary` (when set) corresponds to a known method name in `reference/method-router.md`.
