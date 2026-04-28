# SQL Safety + Causal Correctness Rules

## Safety

- Read-only queries only. Never write, update, delete, create, or mutate warehouse data.
- Use dry-run / cost estimation when available.
- Always apply date filters on large event tables.
- Limit samples; aggregate when possible.
- Do not export raw PII. Redact / hash user identifiers when feasible.
- Store only necessary columns.
- Avoid full table scans unless explicitly approved.
- Ask before running expensive queries.

## Causal correctness

- Define the unit of analysis before joining.
- Avoid many-to-many joins that duplicate units.
- Treatment must be measured before outcome.
- Covariates used for adjustment must be pre-treatment.
- Exclude post-treatment variables from adjustment.
- Define eligibility before treatment assignment.
- Define the comparison group carefully and preserve eligible non-treated users.
- Avoid conditioning on colliders.
- Separate assignment from exposure when noncompliance exists.

## Review output (YAML)

```yaml
approved: true | false
risk_level: low | medium | high
issues:
  - severity: low | medium | high
    description: string
    suggested_fix: string
```
