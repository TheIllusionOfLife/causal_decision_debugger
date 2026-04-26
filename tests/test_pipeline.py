"""End-to-end pipeline tests on synthetic example fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from causal_debugger.pipeline import run
from causal_debugger.scenarios.dgps import no_control, observational_confounding

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "onboarding_retention"


def test_example_pipeline_runs_end_to_end(tmp_path: Path) -> None:
    # Copy example into tmp so the test is hermetic.
    work = tmp_path / "onboarding_retention"
    work.mkdir()
    (work / "causal_spec.yaml").write_text((EXAMPLE_DIR / "causal_spec.yaml").read_text())
    (work / "assumption_ledger.yaml").write_text(
        (EXAMPLE_DIR / "assumption_ledger.yaml").read_text()
    )
    data_dir = work / "data"
    data_dir.mkdir()
    scen = observational_confounding(n=10_000, seed=3)
    df = scen.frame.rename(
        columns={
            "treated": "onboarding_v2_exposed",
            "outcome": "retained_d7",
            "treatment_time": "onboarding_started_at",
            "outcome_time": "d7_window_end_at",
        }
    )
    df["acquisition_channel"] = df["paid_channel"].map({1: "paid", 0: "organic"})
    df["signup_week"] = "2026-W10"
    df.to_parquet(data_dir / "observational.parquet")
    spec_path = work / "causal_spec.yaml"
    spec = yaml.safe_load(spec_path.read_text())
    spec["data"]["local_path"] = str((data_dir / "observational.parquet").resolve())
    spec_path.write_text(yaml.safe_dump(spec))

    result = run(work)
    assert result["status"] == "ok"
    assert (work / "report.md").exists()
    artifacts = work / "artifacts"
    assert (artifacts / "estimates.json").exists()
    assert (artifacts / "robustness.json").exists()
    estimate = json.loads((artifacts / "estimates.json").read_text())
    # Spec deliberately omits motivation_proxy — partial adjustment leaves residual confounding.
    # The estimate should still be positive and within an order of magnitude of truth.
    assert estimate["effect_size"] > 0
    assert estimate["confidence_level"] in ("medium", "low")
    assert estimate["effect_size"] < 0.15


def test_pipeline_handles_no_control(tmp_path: Path) -> None:
    work = tmp_path / "no_control"
    work.mkdir()
    data_dir = work / "data"
    data_dir.mkdir()
    scen = no_control(n=2_000)
    df = scen.frame.rename(
        columns={
            "treated": "onboarding_v2_exposed",
            "outcome": "retained_d7",
            "treatment_time": "onboarding_started_at",
            "outcome_time": "d7_window_end_at",
        }
    )
    df.to_parquet(data_dir / "all_treated.parquet")
    spec = yaml.safe_load((EXAMPLE_DIR / "causal_spec.yaml").read_text())
    spec["data"]["local_path"] = str((data_dir / "all_treated.parquet").resolve())
    spec["causal_question"]["comparison_group"] = ""  # signal: no comparison group
    spec["variables"]["pre_treatment_covariates"] = []
    spec["methods"]["primary"] = None
    (work / "causal_spec.yaml").write_text(yaml.safe_dump(spec))
    (work / "assumption_ledger.yaml").write_text(
        (EXAMPLE_DIR / "assumption_ledger.yaml").read_text()
    )

    result = run(work)
    assert result["status"] == "not_identifiable"
    report = (work / "report.md").read_text()
    assert "Not Identifiable" in report
    assert "Recommended Next Experiment" in report or "Recommended next action" in report.lower()
    failure = json.loads((work / "artifacts" / "identifiability_failure.json").read_text())
    assert failure["identifiability_status"] == "not_identifiable"
