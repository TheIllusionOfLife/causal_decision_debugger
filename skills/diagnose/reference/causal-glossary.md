# Causal Glossary

- **ATE (Average Treatment Effect)** — average causal effect across the full population.
- **ATT (Average Treatment effect on the Treated)** — effect for those who actually received treatment.
- **LATE (Local Average Treatment Effect)** — effect for compliers in IV / encouragement designs.
- **CATE (Conditional Average Treatment Effect)** — effect as a function of covariates.
- **ITT (Intent-To-Treat)** — effect of being assigned to treatment regardless of compliance.
- **Confounder** — variable that affects both treatment and outcome.
- **Collider** — variable affected by both treatment and outcome; conditioning on it induces bias.
- **Mediator** — variable on the causal path from treatment to outcome; should not be controlled when estimating total effect.
- **Pre-treatment covariate** — measured before treatment; safe to use for adjustment.
- **Post-treatment variable** — measured after treatment; not safe for adjustment.
- **Positivity / Overlap** — every covariate stratum has both treated and control units.
- **SUTVA** — stable unit treatment value assumption: no interference between units, single version of treatment.
- **Pre-trend** — outcome trajectory of treated vs control before treatment; used to test the parallel-trends assumption in DiD.
- **Identifiability** — whether the causal question can in principle be answered from available data + assumptions.
- **SMD (Standardized Mean Difference)** — covariate balance metric; conventionally `< 0.1` is acceptable.
- **E-value** — strength of unobserved confounding required to explain away an observed effect.
