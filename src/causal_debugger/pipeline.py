"""End-to-end orchestration: validate → profile → balance → estimate → refute → render."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from causal_debugger.data.balance import check_balance
from causal_debugger.data.io import read_table
from causal_debugger.data.profile import profile_dataframe
from causal_debugger.data.timestamps import check_timestamps
from causal_debugger.methods import (
    ab_test,
    cate,
    did,
    doubly_robust,
    ipw,
    its,
    iv,
    matching,
    rdd,
    synthetic_control,
)
from causal_debugger.methods.router import context_from_spec, suggest_method
from causal_debugger.refutation.placebo import placebo_treatment_test
from causal_debugger.refutation.sensitivity import sensitivity_check
from causal_debugger.refutation.subset import subset_stability
from causal_debugger.reporting.render import render_report
from causal_debugger.spec.validate import validate_spec

# Default design column names. Specs can override via spec["data"]["columns"].
_DEFAULT_DESIGN_COLUMNS: dict[str, Any] = {
    "group": "group",
    "post": "post",
    "period": "period",
    "unit_id": "unit_id",
    "instrument": "instrument",
    "running": "running",
    "treated_unit": 0,
    "rdd_cutoff": 0.0,
}


def _design_columns(spec: dict[str, Any]) -> dict[str, Any]:
    cols = dict(_DEFAULT_DESIGN_COLUMNS)
    cols.update((spec.get("data") or {}).get("columns") or {})
    return cols


def _treat_period(df: pd.DataFrame, post_col: str, period_col: str) -> int:
    """First period at which post == 1. Falls back to median if post is unavailable."""
    if post_col in df.columns and period_col in df.columns:
        post_periods = df.loc[df[post_col].astype(int) == 1, period_col]
        if not post_periods.empty:
            return int(post_periods.astype(int).min())
    if period_col in df.columns:
        return int(df[period_col].astype(int).median())
    raise ValueError(f"Cannot determine treatment period: {period_col!r} not in dataframe.")


def _make_dispatch(spec: dict[str, Any]) -> dict[str, Any]:
    treat = spec["causal_question"]["treatment"]["name"]
    outcome = spec["causal_question"]["outcome"]["name"]
    covariates = spec["variables"]["pre_treatment_covariates"]
    cols = _design_columns(spec)
    return {
        "ab_test_analysis": lambda df: ab_test.estimate_ab(df, treatment=treat, outcome=outcome),
        "regression_adjustment": lambda df: ab_test.estimate_ab(
            df, treatment=treat, outcome=outcome, covariates=covariates
        ),
        "difference_in_differences": lambda df: did.estimate_did(
            df,
            group_col=cols["group"],
            post_col=cols["post"],
            outcome_col=outcome,
            period_col=cols["period"],
        ),
        "interrupted_time_series": lambda df: its.estimate_its(
            df, period_col=cols["period"], post_col=cols["post"], outcome_col=outcome
        ),
        "synthetic_control": lambda df: synthetic_control.estimate_synthetic_control(
            df,
            unit_col=cols["unit_id"],
            period_col=cols["period"],
            outcome_col=outcome,
            treated_unit=cols["treated_unit"],
            treat_period=_treat_period(df, cols["post"], cols["period"]),
        ),
        "propensity_score_weighting": lambda df: ipw.estimate_ipw(
            df, treatment=treat, outcome=outcome, covariates=covariates
        ),
        "matching": lambda df: matching.estimate_matching(
            df, treatment=treat, outcome=outcome, covariates=covariates
        ),
        "doubly_robust_estimation": lambda df: doubly_robust.estimate_doubly_robust(
            df, treatment=treat, outcome=outcome, covariates=covariates
        ),
        "cate": lambda df: cate.estimate_cate(
            df, treatment=treat, outcome=outcome, covariates=covariates
        ),
        "instrumental_variables": lambda df: iv.estimate_iv(
            df, treatment=treat, outcome=outcome, instrument=cols["instrument"]
        ),
        "regression_discontinuity": lambda df: rdd.estimate_rdd(
            df,
            running_var=cols["running"],
            outcome=outcome,
            cutoff=float(cols["rdd_cutoff"]),
        ),
    }


def _load_data(spec: dict[str, Any], analysis_dir: Path) -> pd.DataFrame:
    data_cfg = spec.get("data") or {}
    rel = data_cfg.get("local_path")
    if not rel:
        raise ValueError("causal_spec.data.local_path is required for the local pipeline.")
    candidate = Path(rel)
    if not candidate.is_absolute():
        candidate = (analysis_dir / candidate).resolve()
        if not candidate.exists():
            candidate = (Path.cwd() / rel).resolve()
    return read_table(candidate)


def _audit(df: pd.DataFrame, spec: dict[str, Any]) -> dict[str, Any]:
    profile = profile_dataframe(df)
    treat_col = spec["causal_question"]["treatment"]["name"]
    treat_time = spec["causal_question"]["treatment"].get("treatment_time")
    outcome_time = spec["causal_question"]["outcome"].get("outcome_window")
    cols = _design_columns(spec)
    unit_id_col = cols.get("unit_id_audit") or cols.get("unit_id")
    outcome_time_col = cols.get("outcome_time")
    audit: dict[str, Any] = {"profile": profile}
    if treat_time and outcome_time and treat_time in df.columns:
        # Prefer an explicit outcome_time column from spec.data.columns, then the literal
        # outcome_window value, and only consider unit_id columns that actually exist.
        candidate_outcome_cols = [
            c for c in (outcome_time_col, outcome_time) if c and c in df.columns
        ]
        if candidate_outcome_cols:
            audit["timestamps"] = check_timestamps(
                df,
                treat_time,
                candidate_outcome_cols[0],
                unit_id_col=unit_id_col if unit_id_col in df.columns else None,
            )
    covariates = spec["variables"]["pre_treatment_covariates"]
    if treat_col in df.columns and covariates:
        present = [c for c in covariates if c in df.columns]
        if present:
            audit["balance"] = check_balance(df, treatment_col=treat_col, covariates=present)
    return audit


def _refute(
    df: pd.DataFrame,
    spec: dict[str, Any],
    estimate: dict[str, Any],
    primary_estimator: Any,
) -> list[dict[str, Any]]:
    treat_col = spec["causal_question"]["treatment"]["name"]
    outcome_col = spec["causal_question"]["outcome"]["name"]
    outcome_type = spec["causal_question"]["outcome"].get("type", "binary")
    refutations: list[dict[str, Any]] = []
    if treat_col in df.columns and outcome_col in df.columns:

        def _placebo_estimator(permuted: pd.DataFrame) -> float:
            try:
                return float(primary_estimator(permuted)["effect_size"])
            except Exception:
                # If the primary estimator can't run on the permuted data (e.g. degenerate
                # arms after shuffle), fall back to diff-in-means inside placebo_treatment_test.
                raise

        refutations.append(
            placebo_treatment_test(
                df,
                treatment=treat_col,
                outcome=outcome_col,
                main_estimate=estimate["effect_size"],
                seed=0,
                estimator=_placebo_estimator,
            )
        )

        def _primary_subset(sub: pd.DataFrame) -> float:
            try:
                return float(primary_estimator(sub)["effect_size"])
            except Exception:
                # Some estimators require columns the segment may lack; fall back to
                # difference-in-means so subset stability still produces a signal.
                return float(
                    ab_test.estimate_ab(sub, treatment=treat_col, outcome=outcome_col)[
                        "effect_size"
                    ]
                )

        segment = next(
            (
                c
                for c in spec["variables"]["pre_treatment_covariates"]
                if c in df.columns and df[c].nunique() <= 6
            ),
            None,
        )
        if segment is not None:
            refutations.append(
                subset_stability(
                    df,
                    segment_col=segment,
                    estimator=_primary_subset,
                    main_estimate=estimate["effect_size"],
                )
            )
    refutations.append(
        sensitivity_check(
            main_estimate=estimate["effect_size"],
            ci_low=estimate["confidence_interval"][0],
            ci_high=estimate["confidence_interval"][1],
            baseline_outcome_rate=float(df[outcome_col].mean())
            if outcome_col in df.columns
            else 0.5,
            outcome_type=outcome_type,
        )
    )
    return refutations


def run(analysis_dir: Path) -> dict[str, Any]:
    analysis_dir = Path(analysis_dir).resolve()
    spec_path = analysis_dir / "causal_spec.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    errors = validate_spec(spec)
    if errors:
        raise ValueError(f"causal_spec.yaml is invalid: {[e.message for e in errors]}")

    df = _load_data(spec, analysis_dir)
    audit = _audit(df, spec)

    plan = suggest_method(context_from_spec(spec))
    primary = (spec.get("methods") or {}).get("primary") or plan["primary_method"]
    artifacts_dir = analysis_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _dump(payload: Any) -> str:
        # allow_nan=False so estimator NaNs/Infs fail loudly instead of producing invalid JSON.
        return json.dumps(payload, indent=2, allow_nan=False, default=str)

    if "balance" in audit:
        (artifacts_dir / "balance_check.json").write_text(_dump(audit["balance"]))
    if "timestamps" in audit:
        (artifacts_dir / "timestamp_check.json").write_text(_dump(audit["timestamps"]))
    (artifacts_dir / "eda_summary.json").write_text(_dump(audit["profile"]))
    (analysis_dir / "method_plan.json").write_text(_dump(plan))

    if plan["identifiability_status"] == "not_identifiable" or primary == "not_identifiable":
        failure = {
            "identifiability_status": "not_identifiable",
            "reasons": [plan["reasoning_summary"]]
            if plan["reasoning_summary"]
            else ["No identifiable design."],
            "recommended_next_action": (
                "Run a 10% randomized holdout for 14 days, or instrument the next launch with a "
                "staggered rollout so a comparison group exists."
            ),
            "method_attempted": primary,
        }
        (artifacts_dir / "identifiability_failure.json").write_text(_dump(failure))
        ledger_path = analysis_dir / "assumption_ledger.yaml"
        ledger = yaml.safe_load(ledger_path.read_text()) if ledger_path.exists() else None
        ctx_render = {
            "analysis_id": spec.get("analysis_id"),
            "causal_spec": spec,
            "assumption_ledger": ledger,
            "method_plan": plan,
            "estimate": None,
            "identifiability_failure": failure,
        }
        report = render_report(ctx_render)
        (analysis_dir / "report.md").write_text(report)
        return {"status": "not_identifiable", "report": str(analysis_dir / "report.md")}

    dispatch = _make_dispatch(spec)
    estimator_fn = dispatch.get(primary)
    if estimator_fn is None:
        raise ValueError(f"No estimator wired for primary method {primary!r}")
    estimate = estimator_fn(df)
    (artifacts_dir / "estimates.json").write_text(_dump(estimate))

    refutations = _refute(df, spec, estimate, estimator_fn)
    (artifacts_dir / "robustness.json").write_text(_dump(refutations))

    ledger_path = analysis_dir / "assumption_ledger.yaml"
    ledger = yaml.safe_load(ledger_path.read_text()) if ledger_path.exists() else None
    ctx_render = {
        "analysis_id": spec.get("analysis_id"),
        "causal_spec": spec,
        "assumption_ledger": ledger,
        "method_plan": plan,
        "estimate": estimate,
        "refutation": refutations,
    }
    report = render_report(ctx_render)
    (analysis_dir / "report.md").write_text(report)
    return {
        "status": "ok",
        "estimate": estimate,
        "refutations": refutations,
        "report": str(analysis_dir / "report.md"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis_dir", type=Path)
    args = parser.parse_args(argv)
    result = run(args.analysis_dir.resolve())
    print(json.dumps({"status": result["status"], "report": result.get("report")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
