"""Benign-only anomaly detection under two protocols.

The detector never sees an attack row. It learns the shape of benign traffic and
scores how far a new row sits from it. Two protocols are reported:

- ``loso``: fit on the benign rows of seven scenarios, threshold at the 95th
  percentile of a chronological benign validation split, evaluate on the full
  held-out scenario. Measures cross-scenario transfer.
- ``online``: same fit, threshold calibrated on the first 20 % of the held-out
  scenario (assumed clean warm-up), evaluate on the remaining 80 %. Measures
  per-deployment operation.

The model is used as an anomaly scorer, not as a clusterer, so cluster purity
against attack labels is not the objective. What matters is whether the score
separates attack from benign and whether the calibrated threshold transfers.

Run with: python -m src.unsupervised [--reduce REDUCER]

``--reduce`` applies the same column reduction as ``src/reduce.py`` before the
PCA step, so the reduced and the full-feature detectors can be compared under
the same protocol.
"""

from __future__ import annotations

import argparse
import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import Birch, DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .data import SCENARIOS, build_matrices, load_all
from .features import detrend
from .reduce import REDUCERS, corr_filter, recipe
from .train import recall_at_fpr

SEED = 42
WARMUP = 0.2
QUANTILE = 95
MODELS: tuple[str, ...] = ("kmeans", "birch", "dbscan")


def _pipeline() -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("pca", PCA(n_components=0.95, random_state=SEED)),
        ]
    )


def _fit(model_name: str, Z: np.ndarray):
    """Fit one model on the benign training rows already in PCA space."""
    sample = min(2000, len(Z))

    if model_name == "kmeans":
        best, best_sil = None, -1.0
        for k in range(2, 11):
            candidate = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(Z)
            sil = silhouette_score(
                Z, candidate.labels_, sample_size=sample, random_state=SEED
            )
            if sil > best_sil:
                best, best_sil = candidate, sil
        return best

    if model_name == "birch":
        best, best_sil = None, -1.0
        for threshold in (0.2, 0.5, 1.0):
            candidate = Birch(
                threshold=threshold, branching_factor=50, n_clusters=None
            ).fit(Z)
            labels = candidate.labels_
            if len(np.unique(labels)) < 2:
                continue
            sil = silhouette_score(Z, labels, sample_size=sample, random_state=SEED)
            if sil > best_sil:
                best, best_sil = candidate, sil
        return best if best is not None else Birch(threshold=0.5).fit(Z)

    # dbscan: eps from the 90th percentile of the 5th-nearest-neighbour distance
    neighbours = NearestNeighbors(n_neighbors=5).fit(Z)
    distances, _ = neighbours.kneighbors(Z)
    eps = max(float(np.percentile(distances[:, -1], 90)), 1e-6)
    return DBSCAN(eps=eps, min_samples=5).fit(Z)


def _score(model_name: str, model, Z: np.ndarray) -> np.ndarray:
    """Distance to the nearest benign prototype; larger means more anomalous."""
    if model_name == "kmeans":
        return model.transform(Z).min(axis=1)
    if model_name == "birch":
        neighbours = NearestNeighbors(n_neighbors=1).fit(model.subcluster_centers_)
        return neighbours.kneighbors(Z)[0][:, 0]
    core = model.components_
    if len(core) == 0:
        core = Z
    neighbours = NearestNeighbors(n_neighbors=1).fit(core)
    return neighbours.kneighbors(Z)[0][:, 0]


def _metrics(y_true, score, threshold: float) -> dict:
    y_true = np.asarray(y_true, dtype=int)
    pred = (score > threshold).astype(int)
    tp = int(np.sum((pred == 1) & (y_true == 1)))
    fp = int(np.sum((pred == 1) & (y_true == 0)))
    fn = int(np.sum((pred == 0) & (y_true == 1)))
    tn = int(np.sum((pred == 0) & (y_true == 0)))

    auc = float("nan")
    if len(np.unique(y_true)) == 2:
        auc = float(roc_auc_score(y_true, score))

    return {
        "n_test": len(y_true),
        "n_pos": int(np.sum(y_true)),
        "n_neg": int(len(y_true) - np.sum(y_true)),
        "auc": auc,
        "recall": tp / (tp + fn) if (tp + fn) else float("nan"),
        "specificity": tn / (tn + fp) if (tn + fp) else float("nan"),
        "recall_at_fpr1": recall_at_fpr(y_true, score, 0.01),
        "recall_at_fpr5": recall_at_fpr(y_true, score, 0.05),
        "threshold": threshold,
        "flagged": int(np.sum(pred)),
    }


def _validation_mask(scenario, y_binary, train_mask, fraction: float = 0.2) -> np.ndarray:
    """Last ``fraction`` of each training scenario's benign rows, chronologically."""
    mask = np.zeros(len(y_binary), dtype=bool)
    for name in SCENARIOS:
        rows = np.where(
            train_mask & (scenario == name).to_numpy() & (y_binary == 0).to_numpy()
        )[0]
        if len(rows) == 0:
            continue
        cut = int(len(rows) * (1 - fraction))
        mask[rows[cut:]] = True
    return mask


def _k_of(model_name: str, model) -> float:
    if model_name == "kmeans":
        return float(model.n_clusters)
    if model_name == "birch":
        return float(len(model.subcluster_centers_))
    return float(np.sum(model.labels_ != -1))


def run(
    detrend_method: str = "range",
    window: int = 120,
    quantile: int = QUANTILE,
    reduce_method: str = "none",
):
    warnings.filterwarnings("ignore")
    matrices = build_matrices(load_all())
    X = detrend(matrices.X, matrices.scenario, method=detrend_method, window=window)
    if reduce_method != "none":
        X = recipe(X, reduce_method)
    y = matrices.y_binary
    scenario = matrices.scenario
    position = matrices.position
    print(
        f"features={X.shape[1]} detrend={detrend_method} window={window}s "
        f"reduce={reduce_method} threshold=p{quantile} warmup={WARMUP:.0%}"
    )

    loso_rows, online_rows = [], []
    for held in SCENARIOS:
        test_mask = (scenario == held).to_numpy()
        train_mask = (~test_mask) & (y == 0).to_numpy()
        validation = _validation_mask(scenario, y, train_mask)
        fit_mask = train_mask & ~validation

        # The correlation filter is fitted on the benign training rows only, so
        # the held-out scenario never influences which columns survive. This
        # mirrors the supervised protocol in src/reduce.py.
        Xf = X
        if reduce_method.endswith("_corr"):
            columns = corr_filter(X.loc[fit_mask])
            Xf = X[columns]

        preprocess = _pipeline()
        Z_fit = preprocess.fit_transform(Xf.loc[fit_mask])
        Z_validation = preprocess.transform(Xf.loc[validation])

        warm_mask = test_mask & (position < WARMUP).to_numpy()
        warm_attack = int(np.sum(y[warm_mask]))
        if warm_attack:
            print(f"  warning: {held} warm-up contains {warm_attack} attack rows")

        for model_name in MODELS:
            model = _fit(model_name, Z_fit)
            threshold_loso = float(
                np.percentile(_score(model_name, model, Z_validation), quantile)
            )
            score_test = _score(
                model_name, model, preprocess.transform(Xf.loc[test_mask])
            )
            loso_rows.append(
                {
                    "protocol": "loso",
                    "fold": held,
                    "model": model_name,
                    "k_or_eps": _k_of(model_name, model),
                    **_metrics(y.loc[test_mask], score_test, threshold_loso),
                }
            )

            threshold_online = float(
                np.percentile(
                    _score(
                        model_name,
                        model,
                        preprocess.transform(Xf.loc[warm_mask]),
                    ),
                    quantile,
                )
            )
            rest_mask = test_mask & ~warm_mask
            score_rest = _score(
                model_name, model, preprocess.transform(Xf.loc[rest_mask])
            )
            online_rows.append(
                {
                    "protocol": "online",
                    "fold": held,
                    "model": model_name,
                    "k_or_eps": _k_of(model_name, model),
                    **_metrics(y.loc[rest_mask], score_rest, threshold_online),
                }
            )

        print(f"  {held:6s} fitted on {int(fit_mask.sum()):,} benign rows", flush=True)

    return pd.DataFrame(loso_rows), pd.DataFrame(online_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--detrend",
        default="range",
        choices=("none", "mean", "zscore", "std", "range", "diff"),
    )
    parser.add_argument("--window", type=int, default=120)
    parser.add_argument("--quantile", type=int, default=QUANTILE)
    parser.add_argument(
        "--reduce",
        default="none",
        choices=REDUCERS,
        help="column reduction applied before the detector (default: none)",
    )
    parser.add_argument("--out-loso", default="resultados/unsup_loso.csv")
    parser.add_argument("--out-online", default="resultados/unsup_online.csv")
    args = parser.parse_args(argv)

    loso, online = run(
        detrend_method=args.detrend,
        window=args.window,
        quantile=args.quantile,
        reduce_method=args.reduce,
    )
    loso.to_csv(args.out_loso, index=False)
    online.to_csv(args.out_online, index=False)
    print(f"\nwrote {args.out_loso} and {args.out_online}")
    print("\nLOSO")
    print(loso.round(3).to_string(index=False))
    print("\nONLINE")
    print(online.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
