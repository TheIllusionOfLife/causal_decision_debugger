"""Method router: pick an identification strategy from design facts."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml


@dataclass(frozen=True)
class RouterContext:
    randomized: bool = False
    has_pre_period: bool = False
    rollout_pattern: Literal["single", "staggered", "single_unit", "aggregate_time_series"] = (
        "single"
    )
    threshold_assignment: bool = False
    has_donor_pool: bool = False
    has_instrument: bool = False
    has_pre_treatment_covariates: bool = True
    has_comparison_group: bool = True
    heterogeneous_effect_question: bool = False
    sample_size: int = 0
    pre_treatment_covariate_count: int = 0


def _plan(
    primary: str,
    *,
    secondary: list[str],
    assumptions: list[str],
    diagnostics: list[str],
    refutation: list[str],
    status: str,
    reasoning: str,
) -> dict[str, Any]:
    return {
        "primary_method": primary,
        "secondary_methods": secondary,
        "required_assumptions": assumptions,
        "diagnostics": diagnostics,
        "refutation_tests": refutation,
        "identifiability_status": status,
        "reasoning_summary": reasoning,
    }


def suggest_method(ctx: RouterContext) -> dict[str, Any]:
    if not ctx.has_comparison_group and ctx.rollout_pattern != "aggregate_time_series":
        return _plan(
            "not_identifiable",
            secondary=[],
            assumptions=[],
            diagnostics=[],
            refutation=[],
            status="not_identifiable",
            reasoning=(
                "No comparison group is available. The current data cannot support a causal "
                "estimate; recommend a randomized holdout or staggered rollout next time."
            ),
        )

    if ctx.threshold_assignment:
        return _plan(
            "regression_discontinuity",
            secondary=[],
            assumptions=[
                "no_manipulation_around_threshold",
                "smoothness_of_potential_outcomes",
            ],
            diagnostics=["density_of_running_variable", "covariate_continuity"],
            refutation=["bandwidth_sensitivity", "placebo_threshold"],
            status="identifiable",
            reasoning="Treatment is assigned by a threshold rule; RDD identifies the LATE at the cutoff.",
        )

    if ctx.has_instrument:
        return _plan(
            "instrumental_variables",
            secondary=["intent_to_treat"],
            assumptions=["instrument_relevance", "exclusion_restriction", "monotonicity"],
            diagnostics=["weak_instrument_F_stat", "first_stage_sign"],
            refutation=["overidentification_test", "alternate_instrument"],
            status="weakly_identifiable",
            reasoning="An instrument is available; 2SLS recovers the LATE under standard IV assumptions.",
        )

    if ctx.randomized:
        return _plan(
            "ab_test_analysis",
            secondary=["regression_adjustment", "cuped"],
            assumptions=["randomization", "stable_unit_treatment_value"],
            diagnostics=["sample_ratio_mismatch", "covariate_balance"],
            refutation=["aa_test", "subset_stability"],
            status="identifiable",
            reasoning="Treatment is randomized; difference-in-means is unbiased and ATE is identified by design.",
        )

    if ctx.rollout_pattern == "staggered" and ctx.has_pre_period:
        return _plan(
            "difference_in_differences",
            secondary=["regression_adjustment"],
            assumptions=["parallel_trends", "no_anticipation", "stable_composition"],
            diagnostics=["pre_trend_test", "balance_pre_period"],
            refutation=["placebo_outcome", "alternative_event_window"],
            status="weakly_identifiable",
            reasoning="Staggered rollout with a pre-period; DiD is the canonical design.",
        )

    if ctx.rollout_pattern == "single_unit" and ctx.has_donor_pool and ctx.has_pre_period:
        return _plan(
            "synthetic_control",
            secondary=["interrupted_time_series"],
            assumptions=["good_pre_period_fit", "no_anticipation"],
            diagnostics=["pre_period_mspe", "donor_weight_concentration"],
            refutation=["leave_one_out_donors", "in_time_placebo"],
            status="weakly_identifiable",
            reasoning="A treated unit has a donor pool with a long pre-period; synthetic control fits well.",
        )

    if ctx.rollout_pattern == "aggregate_time_series" and ctx.has_pre_period:
        return _plan(
            "interrupted_time_series",
            secondary=[],
            assumptions=["no_simultaneous_change", "stable_seasonality"],
            diagnostics=["pre_period_fit", "autocorrelation_check"],
            refutation=["placebo_event_date", "alternative_specification"],
            status="weakly_identifiable",
            reasoning="Only an aggregate time series is available; ITS provides a level/slope-shift estimate.",
        )

    if ctx.has_pre_treatment_covariates:
        primary = "doubly_robust_estimation"
        secondary = ["propensity_score_weighting", "matching"]
        if ctx.heterogeneous_effect_question:
            secondary = ["cate", *secondary]
        return _plan(
            primary,
            secondary=secondary,
            assumptions=[
                "no_unobserved_confounding",
                "positivity_overlap",
                "treatment_precedes_outcome",
            ],
            diagnostics=[
                "covariate_balance_check",
                "propensity_overlap_check",
                "missingness_check",
            ],
            refutation=[
                "placebo_outcome",
                "subset_stability",
                "sensitivity_to_unobserved_confounding",
            ],
            status="weakly_identifiable",
            reasoning=(
                "Observational user-level treatment with rich pre-treatment covariates. "
                "Doubly robust earns trust against either propensity or outcome misspecification; "
                "IPW and matching are kept as sanity-check secondaries."
            ),
        )

    return _plan(
        "not_identifiable",
        secondary=[],
        assumptions=[],
        diagnostics=[],
        refutation=[],
        status="not_identifiable",
        reasoning="Design facts are insufficient to identify a causal effect.",
    )


def context_from_spec(spec: dict[str, Any]) -> RouterContext:
    """Best-effort mapping from a causal_spec dict to RouterContext defaults."""
    variables = spec.get("variables") or {}
    pre = variables.get("pre_treatment_covariates") or []
    methods = spec.get("methods") or {}
    return RouterContext(
        randomized=False,
        has_pre_period=False,
        rollout_pattern="single",
        threshold_assignment=False,
        has_donor_pool=False,
        has_instrument=False,
        has_pre_treatment_covariates=bool(pre),
        has_comparison_group=bool(spec.get("causal_question", {}).get("comparison_group")),
        heterogeneous_effect_question=bool(methods.get("heterogeneous_effect")),
        sample_size=0,
        pre_treatment_covariate_count=len(pre),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="Path to causal_spec.yaml")
    parser.add_argument("--out", type=Path, default=None, help="Write method_plan.json")
    parser.add_argument("--randomized", action="store_true")
    parser.add_argument("--has-pre-period", action="store_true")
    parser.add_argument(
        "--rollout-pattern",
        choices=["single", "staggered", "single_unit", "aggregate_time_series"],
        default="single",
    )
    parser.add_argument("--threshold-assignment", action="store_true")
    parser.add_argument("--has-donor-pool", action="store_true")
    parser.add_argument("--has-instrument", action="store_true")
    parser.add_argument("--no-comparison-group", action="store_true")
    parser.add_argument("--heterogeneous", action="store_true")
    args = parser.parse_args(argv)
    spec = yaml.safe_load(args.spec.resolve().read_text(encoding="utf-8"))
    ctx = context_from_spec(spec)
    ctx = RouterContext(
        randomized=args.randomized,
        has_pre_period=args.has_pre_period,
        rollout_pattern=args.rollout_pattern,
        threshold_assignment=args.threshold_assignment,
        has_donor_pool=args.has_donor_pool,
        has_instrument=args.has_instrument,
        has_pre_treatment_covariates=ctx.has_pre_treatment_covariates,
        has_comparison_group=(not args.no_comparison_group) and ctx.has_comparison_group,
        heterogeneous_effect_question=args.heterogeneous,
        sample_size=ctx.sample_size,
        pre_treatment_covariate_count=ctx.pre_treatment_covariate_count,
    )
    plan = suggest_method(ctx)
    if args.out:
        out = args.out.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, indent=2))
    else:
        print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
