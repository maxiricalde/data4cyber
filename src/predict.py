"""Score a scenario table with one of the saved production models.

The input CSV must use the dataset format (the same columns as
``datasets/datasetS*.csv``), because the feature recipe expects the full
measurement table and the label columns used to build the matrix.

Examples
--------
Supervised score on S6:
    python -m src.predict --model supervised --csv datasets/datasetS6.csv

Unsupervised score with a 360-row warm-up calibration:
    python -m src.predict --model unsupervised --csv datasets/datasetS6.csv --warmup 360

The warm-up recalibrates the threshold at the 95th percentile of the first N
scores. It is optional: without it the training threshold is used, which is the
honest cross-scenario operating point.
"""

from __future__ import annotations

import argparse

import joblib
import numpy as np
import pandas as pd

from .data import build_matrices
from .features import detrend
from .reduce import average_dimensionless, physical_features
from .unsupervised import _score


def _load(path: str):
    frame = pd.read_csv(path).assign(scenario="target")
    return build_matrices(frame)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("supervised", "unsupervised"), required=True)
    parser.add_argument(
        "--variant",
        choices=("base", "reduced"),
        default="base",
        help="base uses the 139 features; reduced uses the physical recipe (15-16)",
    )
    parser.add_argument("--csv", required=True, help="scenario table in dataset format")
    parser.add_argument(
        "--warmup",
        type=int,
        default=0,
        help="recalibrate the threshold on the first N rows (unsupervised only)",
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    suffix = "" if args.variant == "base" else "_reduced"
    bundle = joblib.load(f"modelos/{args.model}{suffix}.joblib")
    matrices = _load(args.csv)
    X = detrend(matrices.X, matrices.scenario, method=bundle["detrend"], window=bundle["window"])
    if bundle.get("reduce") == "physical_corr":
        X = physical_features(X)
    elif bundle.get("reduce") == "avg_dimensionless":
        X = average_dimensionless(X)
    if bundle.get("columns"):
        X = X[bundle["columns"]]

    if args.model == "supervised":
        score = bundle["pipeline"].predict_proba(X)[:, 1]
        threshold = float(bundle["threshold"])
    else:
        score = _score("kmeans", bundle["model"], bundle["preprocess"].transform(X))
        threshold = float(bundle["threshold"])
        if args.warmup > 0:
            threshold = float(np.percentile(score[: args.warmup], 95))

    result = pd.DataFrame(
        {
            "row": np.arange(len(score)),
            "score": score,
            "flag": (score > threshold).astype(int),
        }
    )

    print(f"model={args.model} rows={len(score):,} threshold={threshold:.4f}")
    print(f"flagged={int(result['flag'].sum()):,} ({result['flag'].mean():.1%})")
    print(result["score"].describe().round(4).to_string())

    if args.out:
        result.to_csv(args.out, index=False)
        print(f"wrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
