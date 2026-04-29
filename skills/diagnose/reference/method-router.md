# Method Router

Pick the identification strategy from the design first, not from model fashion.

| Situation | Recommended primary method | Notes |
|---|---|---|
| Proper randomized experiment | A/B analysis (z-test / OLS), regression adjustment, CUPED | Highest confidence if implemented correctly. |
| Randomized rollout with noncompliance | Instrumental variables (2SLS), intent-to-treat | Separate assignment from exposure. |
| Gradual rollout by date / region / team | Difference-in-differences | Requires pre-trend checks. |
| Product launch with aggregate time series only | Interrupted time series | Weak without external control. |
| Treated group plus donor pool | Synthetic control | Good for geo / market interventions. |
| Threshold-based assignment | Regression discontinuity | Requires no manipulation around threshold. |
| Observational user-level treatment with rich covariates | IPW / matching / doubly robust | Requires no unobserved confounding + overlap. |
| Heterogeneous-effect question | CATE / causal forest / uplift | Requires enough sample size. |
| Metric drop / root-cause investigation | Causal graph + attribution + time-series checks | Often diagnostic, not definitive. |
| No control, no pre-period, simultaneous changes | Not identifiable | Recommend a future experiment design. |

## Method plan must capture

- `identifiability_status`: `identifiable | weakly_identifiable | not_identifiable`.
- `primary_method` and `secondary_methods`.
- `required_assumptions`.
- `diagnostics` to run before estimation.
- `refutation_tests` to run after estimation.
- `reasoning_summary`: why this method was chosen and why others were not.
