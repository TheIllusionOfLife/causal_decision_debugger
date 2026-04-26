# Report Template + Language Rules

## Required sections of `report.md`

1. Executive Summary
2. Decision Context
3. Causal Question
4. Data Used
5. Method Summary
6. Main Result
7. Confidence Level
8. Assumption Ledger Summary
9. Robustness and Refutation Checks
10. Limitations
11. Recommended Decision
12. Recommended Next Experiment or Data Collection
13. Technical Appendix Link

## Confidence levels

- `high` — randomized or strong quasi-experimental design with passing diagnostics and plausible assumptions.
- `medium` — observational or quasi-experimental design with reasonable diagnostics but meaningful assumption risk.
- `low` — serious confounding, weak comparison group, poor overlap, or unstable results.
- `not_identifiable` — the available data / design cannot answer the causal question.

## Forbidden phrases when `confidence != "high"`

The report-quality test rejects rendered reports containing any of these:

- `proved that`
- `definitely caused`
- `guaranteed impact`
- `caused <metric> to (increase|decrease)` (regex)

## Preferred language under uncertainty

- "under the stated assumptions"
- "estimated effect"
- "likely"
- "consistent with"
- "confidence is medium / low"

## Not-identifiable reports

When `identifiability_failure.json` exists, lead with:

> ## Result: Not Identifiable With Current Data

then list reasons and the recommended next action. Do not include a numeric effect estimate.
