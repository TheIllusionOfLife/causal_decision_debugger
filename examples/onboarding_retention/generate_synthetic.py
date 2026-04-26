"""Generate the example onboarding_retention dataset by reusing the observational DGP.

Usage::

    uv run python examples/onboarding_retention/generate_synthetic.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

from causal_debugger.scenarios.dgps import observational_confounding


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data",
        help="Output directory for the generated parquet file.",
    )
    parser.add_argument("--n", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    scenario = observational_confounding(n=args.n, seed=args.seed)
    df = scenario.frame.rename(
        columns={
            "treated": "onboarding_v2_exposed",
            "outcome": "retained_d7",
            "treatment_time": "onboarding_started_at",
            "outcome_time": "d7_window_end_at",
        }
    )
    df["acquisition_channel"] = df["paid_channel"].map({1: "paid", 0: "organic"})
    df["signup_week"] = "2026-W10"
    out_path = args.out_dir / "observational.parquet"
    df.to_parquet(out_path, index=False)
    import json

    truth_path = args.out_dir / "truth.json"
    truth_path.write_text(
        json.dumps(
            {
                "true_ate": scenario.truth["true_ate"],
                "expected_status": scenario.truth["expected_status"],
            }
        )
        + "\n"
    )
    print(f"wrote {out_path} ({len(df)} rows)")


if __name__ == "__main__":
    main()
