# Assumption Ledger Guide

Every causal claim depends on assumptions. The ledger is how the system makes them explicit and testable.

## Status values

- `confirmed` — verified empirically or by design (e.g., randomized assignment).
- `plausible` — domain-supported but not directly checked.
- `uncertain` — could be either way; flagged for follow-up.
- `weak` — likely violated to some degree.
- `violated` — actively known to be false.
- `unknown` — not yet investigated.

## Importance values

- `low` — affects edge cases.
- `medium` — affects magnitude but not direction.
- `high` — could change the sign of the conclusion.
- `critical` — without this assumption the analysis cannot be causal.

## Required fields per entry

- `id` — short stable identifier (e.g. `A1`).
- `name` — human-readable name.
- `status`, `importance`.
- `evidence` — what supports the current status.
- `risk_if_false` — what breaks if the assumption fails.
- `how_to_check_or_improve` — actionable next step.

The schema lives at `src/causal_debugger/schemas/assumption_ledger.schema.json`.
