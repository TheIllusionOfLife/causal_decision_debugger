# onboarding_retention_2026_03 — Causal Decision Report

## Executive Summary

AIPW ATE = +0.0644 (95% CI [+0.0513, +0.0775]) — doubly robust against propensity or outcome misspecification.

**Confidence:** medium.

## Decision Context

Should we keep onboarding_v2?

## Causal Question

- **Unit:** user
- **Treatment:** onboarding_v2_exposed
- **Outcome:** retained_d7
- **Comparison group:** eligible users not exposed to onboarding_v2

## Data Used

examples/onboarding_retention/data/observational.parquet

## Method Summary

- **Primary method:** `doubly_robust_estimation`
- **Secondary methods:** `propensity_score_weighting, matching`
- **Identifiability:** `weakly_identifiable`

## Main Result

Estimated **ATE = +0.0644 outcome_units** (95% CI [+0.0513, +0.0775]).

Sample size: 20,000 (8,925 treated / 11,075 control).

**Diagnostics:**
- propensity_overlap: `passed` — Share of units with PS in tails: 0.000

## Confidence Level

**medium** — Observational or quasi-experimental design with reasonable diagnostics but meaningful assumption risk: Observational user-level treatment with rich pre-treatment covariates. Doubly robust earns trust against either propensity or outcome misspecification; IPW and matching are kept as sanity-check secondaries.

## Assumption Ledger Summary

- **[A1] Treatment happened before outcome** — status: `confirmed`, importance: `critical`. onboarding_started_at occurs before D7 retention window
- **[A2] No major simultaneous change** — status: `unknown`, importance: `high`. Rollout calendar not yet inspected.
- **[A3] No unobserved confounding after adjustment** — status: `weak`, importance: `critical`. Country, device, channel, signup week available; user motivation not.
- **[A4] Positivity / overlap on covariates** — status: `unknown`, importance: `high`. Not yet checked.

## Robustness and Refutation Checks

- **placebo_treatment** — `passed`. Shuffled treatment yields effect -0.0130; main estimate is +0.0644. (Δ vs main: -0.0773)
- **subset_stability** — `passed`. Per-segment estimates: BR: +0.0551, DE: +0.0660, JP: +0.0725, US: +0.0635; max |Δ vs main| = 0.0092 (Δ vs main: +0.0092)
- **sensitivity_to_unobserved_confounding** — `warning`. E-value at point estimate ≈ 1.70; at CI bound ≈ 1.59. Higher E-values mean stronger confounding is needed to explain the effect away.

## Limitations

Treatment was not confirmed randomized; unobserved confounding may remain. See assumption ledger for the load-bearing assumptions.

## Recommended Decision

Provisionally accept the estimated effect under the stated assumptions. Consider a randomized holdout before declaring final impact.

## Recommended Next Experiment or Data Collection

Run a 10% randomized holdout for 14 days, or instrument the next launch with a staggered rollout.

## Technical Appendix

See `technical_appendix.md`.
