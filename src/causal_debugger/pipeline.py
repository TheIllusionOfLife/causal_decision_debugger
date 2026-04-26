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

METHOD_DISPATCH = {
    "ab_test_analysis": lambda df, spec: ab_test.estimate_ab(
        df,
        treatment=spec["causal_question"]["treatment"]["name"],
        outcome=spec["causal_question"]["outcome"]["name"],
    ),
    "regression_adjustment": lambda df, spec: ab_test.estimate_ab(
        df,
        treatment=spec["causal_question"]["treatment"]["name"],
        outcome=spec["causal_question"]["outcome"]["name"],
        covariates=spec["variables"]["pre_treatment_covariates"],
    ),
    "difference_in_differences": lambda df, spec: did.estimate_did(
        df, group_col="group", post_col="post", outcome_col="outcome"
    ),
    "interrupted_time_series": lambda df, spec: its.estimate_its(
        df, period_col="period", post_col="post", outcome_col="outcome"
    ),
    "synthetic_control": lambda df, spec: synthetic_control.estimate_synthetic_control(
        df,
        unit_col="unit_id",
        period_col="period",
        outcome_col="outcome",
        treated_unit=0,
        treat_period=int(df["period"].median()),
    ),
    "propensity_score_weighting": lambda df, spec: ipw.estimate_ipw(
        df,
        treatment=spec["causal_question"]["treatment"]["name"],
        outcome=spec["causal_question"]["outcome"]["name"],
        covariates=spec["variables"]["pre_treatment_covariates"],
    ),
    "matching": lambda df, spec: matching.estimate_matching(
        df,
        treatment=spec["causal_question"]["treatment"]["name"],
        outcome=spec["causal_question"]["outcome"]["name"],
        covariates=spec["variables"]["pre_treatment_covariates"],
    ),
    "doubly_robust_estimation": lambda df, spec: doubly_robust.estimate_doubly_robust(
        df,
        treatment=spec["causal_question"]["treatment"]["name"],
        outcome=spec["causal_question"]["outcome"]["name"],
        covariates=spec["variables"]["pre_treatment_covariates"],
    ),
    "cate": lambda df, spec: cate.estimate_cate(
        df,
        treatment=spec["causal_question"]["treatment"]["name"],
        outcome=spec["causal_question"]["outcome"]["name"],
        covariates=spec["variables"]["pre_treatment_covariates"],
    ),
    "instrumental_variables": lambda df, spec: iv.estimate_iv(
        df,
        treatment=spec["causal_question"]["treatment"]["name"],
        outcome=spec["causal_question"]["outcome"]["name"],
        instrument="instrument",
    ),
    "regression_discontinuity": lambda df, spec: rdd.estimate_rdd(
        df, running_var="running", outcome="outcome", cutoff=0.0
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
    return pd.read_parquet(candidate)


def _audit(df: pd.DataFrame, spec: dict[str, Any]) -> dict[str, Any]:
    profile = profile_dataframe(df)
    treat_col = spec["causal_question"]["treatment"]["name"]
    treat_time = spec["causal_question"]["treatment"].get("treatment_time")
    outcome_time = spec["causal_question"]["outcome"].get("outcome_window")
    audit: dict[str, Any] = {"profile": profile}
    if treat_time and outcome_time and treat_time in df.columns:
        outcome_col = outcome_time if outcome_time in df.columns else "d7_window_end_at"
        if outcome_col in df.columns:
            audit["timestamps"] = check_timestamps(
                df,
                treat_time,
                outcome_col,
                unit_id_col="user_id" if "user_id" in df.columns else None,
            )
    covariates = spec["variables"]["pre_treatment_covariates"]
    if treat_col in df.columns and covariates:
        present = [c for c in covariates if c in df.columns]
        if present:
            audit["balance"] = check_balance(df, treatment_col=treat_col, covariates=present)
    return audit


def _refute(
    df: pd.DataFrame, spec: dict[str, Any], estimate: dict[str, Any]
) -> list[dict[str, Any]]:
    treat_col = spec["causal_question"]["treatment"]["name"]
    outcome_col = spec["causal_question"]["outcome"]["name"]
    refutations: list[dict[str, Any]] = []
    if treat_col in df.columns and outcome_col in df.columns:
        refutations.append(
            placebo_treatment_test(
                df,
                treatment=treat_col,
                outcome=outcome_col,
                main_estimate=estimate["effect_size"],
                seed=0,
            )
        )

        def _ab_estimator(sub: pd.DataFrame) -> float:
            return float(
                ab_test.estimate_ab(sub, treatment=treat_col, outcome=outcome_col)["effect_size"]
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
                    estimator=_ab_estimator,
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

    if "balance" in audit:
        (artifacts_dir / "balance_check.json").write_text(json.dumps(audit["balance"], indent=2))
    if "timestamps" in audit:
        (artifacts_dir / "timestamp_check.json").write_text(
            json.dumps(audit["timestamps"], indent=2, default=str)
        )
    (artifacts_dir / "eda_summary.json").write_text(json.dumps(audit["profile"], indent=2))
    (analysis_dir / "method_plan.json").write_text(json.dumps(plan, indent=2))

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
        (artifacts_dir / "identifiability_failure.json").write_text(json.dumps(failure, indent=2))
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

    estimator_fn = METHOD_DISPATCH.get(primary)
    if estimator_fn is None:
        raise ValueError(f"No estimator wired for primary method {primary!r}")
    estimate = estimator_fn(df, spec)
    (artifacts_dir / "estimates.json").write_text(json.dumps(estimate, indent=2))

    refutations = _refute(df, spec, estimate)
    (artifacts_dir / "robustness.json").write_text(json.dumps(refutations, indent=2))

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
