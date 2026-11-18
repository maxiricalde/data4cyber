"""Train and persist the two production models.

Two variants:

- ``base``: Random Forest on the 139 rolling-range (120 s) features. Transfer to
  unseen benign S0 is specificity 0.943 at AUC 0.912.
- ``reduced``: the same model on the 15-16 columns left by the chosen recipe:
  average the grid frequency only (one grid, five redundant sensors), keep
  ``cos_phi`` per meter, then filter correlated columns. Transfer to S0 is
  specificity 0.996 at AUC 0.943, with recall@5% 0.637. Powers, currents and
  voltages are never averaged, because the five meters measure different
  components.

The unsupervised bundle follows the same recipe. Each bundle stores the feature
recipe (detrend method, window, optional averaging and column list) and the
threshold, so ``src/predict.py`` reproduces the exact transformation.

Run with: python -m src.production [--variant base|reduced]
"""

from __future__ import annotations

import argparse
import os

import joblib
import numpy as np

from .data import build_matrices, load_all
from .features import detrend
from .pipeline import balanced_weights, build_pipeline, make_model
from .reduce import corr_filter, physical_features
from .unsupervised import _fit, _pipeline, _score

DETREND = "range"
WINDOW = 120
OUTPUT_DIR = "modelos"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("base", "reduced"), default="base")
    args = parser.parse_args(argv)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    matrices = build_matrices(load_all())
    X = detrend(matrices.X, matrices.scenario, method=DETREND, window=WINDOW)
    y = matrices.y_binary
    benign = (y == 0).to_numpy()

    recipe: dict = {}
    if args.variant == "reduced":
        X = physical_features(X)
        columns = corr_filter(X)
        X = X[columns]
        recipe = {"reduce": "physical_corr", "columns": columns}

    suffix = "" if args.variant == "base" else "_reduced"

    supervised = build_pipeline(make_model("rf"))
    supervised.fit(X, y, model__sample_weight=balanced_weights(y))
    # 0.5 is the operating point used in every LOSO table. A p95 threshold on
    # training benign collapses to ~0.008 because the balanced Random Forest is
    # extremely confident on benign rows; it is reported in the notebook, not used
    # as the production default.
    supervised_threshold = 0.5
    joblib.dump(
        {
            "pipeline": supervised,
            "detrend": DETREND,
            "window": WINDOW,
            "threshold": supervised_threshold,
            **recipe,
        },
        f"{OUTPUT_DIR}/supervised{suffix}.joblib",
    )

    preprocess = _pipeline()
    Z = preprocess.fit_transform(X.loc[benign])
    kmeans = _fit("kmeans", Z)
    unsupervised_threshold = float(np.percentile(_score("kmeans", kmeans, Z), 95))
    joblib.dump(
        {
            "preprocess": preprocess,
            "model": kmeans,
            "detrend": DETREND,
            "window": WINDOW,
            "threshold": unsupervised_threshold,
            **recipe,
        },
        f"{OUTPUT_DIR}/unsupervised{suffix}.joblib",
    )

    print(
        f"supervised{suffix}   threshold={supervised_threshold:.4f} -> "
        f"{OUTPUT_DIR}/supervised{suffix}.joblib"
    )
    print(
        f"unsupervised{suffix} threshold={unsupervised_threshold:.4f} -> "
        f"{OUTPUT_DIR}/unsupervised{suffix}.joblib"
    )
    print(f"features={X.shape[1]} detrend={DETREND} window={WINDOW}s variant={args.variant}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
