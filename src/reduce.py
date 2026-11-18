"""Column reduction without averaging raw measurements.

The first version of this experiment averaged each signal across the five AC
meters (substation, PV inverter, battery inverter, load A, load B). A physics
review rejected that: those five meters measure different components with
different ratings and roles, so the mean of, for example, ``p_sum3`` is not a
physical quantity. This version never averages currents, powers or voltages.

Only one quantity is averaged, and only because it is the same physical
quantity seen by five redundant sensors: the grid frequency (one grid). The
power factor ``cos_phi`` is dimensionless but is NOT averaged: the meters are
sources and loads with opposite signs and 100x different variability, so its
mean is an aggregate index, not a measurement.

Everything else is reduced by selection (correlation filter, domain selection)
or by PCA.

Techniques compared, all over the same LOSO protocol and the same detrended
features as the main model (range, 120 s):

- ``none``: no reduction (139 features).
- ``corr``: drop one of each pair with |r| > 0.95, fitted on the training folds.
- ``pca``: PCA retaining 95 % of the variance, fitted on the training folds.
- ``dimensionless``: domain selection; keep the dimensionless signals of every
  meter plus battery SOC and the scenario profile.
- ``dimensionless_corr``: domain selection followed by the correlation filter.
- ``physical_corr``: the chosen recipe. Average only the grid frequency (one
  grid seen by five redundant sensors), keep ``cos_phi`` per meter, then filter
  correlated columns. Every surviving column is a real per-component signal.
- ``block_pca``: cluster-then-PCA (direct VARCLUS variant). Hierarchical
  clustering of the columns on ``1 - |r|`` (average linkage, cut at |r| > 0.70)
  and one PCA per block retaining 95 % of that block's variance. Unlike global
  PCA, no component mixes meters with opposite roles, so the result stays
  tree-friendly. Best mean AUC measured (0.952 with rf), but its cut is a
  hyperparameter and it is not the shipped recipe.
- ``avg_dimensionless``: average both dimensionless signals across meters. Kept
  only as evidence: averaging ``cos_phi`` is not physically justified, because
  the meters are sources and loads with opposite signs and very different
  variability.

Run with: python -m src.reduce
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.decomposition import PCA
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .data import SCENARIOS, build_matrices, load_all
from .features import detrend
from .pipeline import balanced_weights, build_pipeline, make_model
from .train import recall_at_fpr

SEED = 42
CORR_THRESHOLD = 0.95
CORR_BLOCK_THRESHOLD = 0.70

# Signals that mean the same thing on every AC meter. Powers, currents and
# voltages do not: each meter sees a different component of the plant.
DIMENSIONLESS_SIGNALS: tuple[str, ...] = ("cos_phi1", "cos_phi2", "cos_phi3", "freq")
CONTEXT_PREFIXES: tuple[str, ...] = ("Battery-SOC-Reference", "Battery-SOC-Reported", "Profile")

REDUCERS: tuple[str, ...] = (
    "none",
    "corr",
    "pca",
    "dimensionless",
    "dimensionless_corr",
    "physical_corr",
    "block_pca",
    "avg_dimensionless",
)


def corr_filter(X_train: pd.DataFrame, threshold: float = CORR_THRESHOLD) -> list[str]:
    """Keep one column per highly-correlated group (greedy, column order)."""
    corr = X_train.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1))
    return [c for c in X_train.columns if not (upper[c] > threshold).any()]


def corr_blocks(
    X_train: pd.DataFrame, threshold: float = CORR_BLOCK_THRESHOLD
) -> pd.Series:
    """Group columns that move together, by hierarchical clustering.

    Deterministic: agglomerative clustering (average linkage) on the distance
    ``1 - |r|``, cut at ``1 - threshold``. Average linkage constrains the mean
    distance of a merged cluster, not each pair: measured on the detrended
    training rows with S0 held out, 2 of the 21 multi-column blocks contain a
    pair below 0.70, the weakest being ``|r| = 0.609``. The cut is the only
    tunable knob; at 0.95 the blocks degenerate into the correlation filter, at
    0.70 they recover physically coherent families (the five meters' ``freq``,
    the line currents of the whole plant, the profile irradiance cluster).
    """
    corr = X_train.corr().abs().fillna(0.0).to_numpy()
    distance = 1.0 - corr
    np.fill_diagonal(distance, 0.0)
    distance = (distance + distance.T) / 2.0
    np.clip(distance, 0.0, None, out=distance)
    tree = linkage(squareform(distance, checks=False), method="average")
    labels = fcluster(tree, t=1.0 - threshold, criterion="distance")
    return pd.Series(labels, index=X_train.columns, name="block")


def block_pca(
    X_train: pd.DataFrame, X_test: pd.DataFrame, variance: float = 0.95
) -> tuple[np.ndarray, np.ndarray]:
    """Run one PCA inside each correlation block.

    Every step (imputation, variance filter, block structure, scaler and PCA)
    is fitted on the training block only, so the held-out scenario never
    informs the grouping or the rotation.
    """
    imputer = SimpleImputer(strategy="median", add_indicator=False).fit(X_train)
    train = pd.DataFrame(imputer.transform(X_train), columns=X_train.columns)
    test = pd.DataFrame(imputer.transform(X_test), columns=X_test.columns)
    keep = VarianceThreshold().fit(train).get_support()
    train, test = train.loc[:, keep], test.loc[:, keep]

    groups = corr_blocks(train)
    train_parts: list[np.ndarray] = []
    test_parts: list[np.ndarray] = []
    for _, columns in groups.groupby(groups):
        names = list(columns.index)
        scaler = StandardScaler().fit(train[names])
        train_block = scaler.transform(train[names])
        test_block = scaler.transform(test[names])
        if len(names) > 1:
            pca = PCA(n_components=variance, random_state=SEED).fit(train_block)
            train_parts.append(pca.transform(train_block))
            test_parts.append(pca.transform(test_block))
        else:
            # A singleton block is a real signal: keep it untouched.
            train_parts.append(train_block)
            test_parts.append(test_block)
    return np.hstack(train_parts), np.hstack(test_parts)


def _signal(column: str) -> str:
    return column.split(".", 1)[1] if "." in column else column


def _prefix(column: str) -> str:
    return column.split(".", 1)[0]


def dimensionless_columns(X: pd.DataFrame) -> list[str]:
    """Columns that are physically comparable across meters, plus context."""
    keep = []
    for column in X.columns:
        if _prefix(column).endswith("Meter"):
            if _signal(column) in DIMENSIONLESS_SIGNALS:
                keep.append(column)
        elif _prefix(column) in CONTEXT_PREFIXES:
            keep.append(column)
    return keep


def physical_features(X: pd.DataFrame) -> pd.DataFrame:
    """The chosen recipe before the correlation filter.

    Frequency is the only signal averaged across meters: it is one grid seen by
    five redundant sensors (means differ by 0.001 Hz, cross-meter r is
    0.97-0.996). ``cos_phi`` stays per meter, because sources and loads have
    opposite signs and 100x different variability, so their mean is an index,
    not a measurement.
    """
    out = X[dimensionless_columns(X)].copy()
    freq = [c for c in X.columns if _prefix(c).endswith("Meter") and _signal(c) == "freq"]
    out = out.drop(columns=[c for c in freq if c in out.columns])
    out["freq"] = X[freq].mean(axis=1)
    return out


def average_dimensionless(X: pd.DataFrame) -> pd.DataFrame:
    """Average only the commensurable signals; keep everything else intact.

    Averaging ``cos_phi`` and ``freq`` across meters is meaningful (same grid,
    dimensionless ratio). Averaging powers, currents or voltages is not, so
    those columns are never touched here.
    """
    meter = [c for c in X.columns if _prefix(c).endswith("Meter")]
    out = X.drop(columns=meter).copy()
    for signal in DIMENSIONLESS_SIGNALS:
        cols = [c for c in meter if _signal(c) == signal]
        if cols:
            out[signal] = X[cols].mean(axis=1)
    return out


def _pca_pipeline(model_name: str, variance: float = 0.95) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=False)),
            ("variance", VarianceThreshold()),
            ("scale", StandardScaler()),
            ("pca", PCA(n_components=variance, random_state=SEED)),
            ("model", make_model(model_name)),
        ]
    )


def _loso(X, y, scenario, model_name, reducer="none"):
    aucs = []
    recalls_5 = []
    recalls_1 = []
    spec_s0 = float("nan")
    kept = []
    for held in SCENARIOS:
        test = (scenario == held).to_numpy()
        train = ~test
        Xtr, Xte = X.loc[train], X.loc[test]
        ytr = y.loc[train]

        if reducer == "block_pca":
            Xtr_b, Xte_b = block_pca(Xtr, Xte)
            kept.append(Xtr_b.shape[1])
            model = make_model(model_name)
            model.fit(Xtr_b, ytr, sample_weight=balanced_weights(ytr))
            score = model.predict_proba(Xte_b)[:, 1]
        else:
            if reducer in ("corr", "dimensionless_corr", "physical_corr"):
                columns = corr_filter(Xtr)
                kept.append(len(columns))
                Xtr, Xte = Xtr[columns], Xte[columns]

            if reducer == "pca":
                pipe = _pca_pipeline(model_name)
            else:
                pipe = build_pipeline(make_model(model_name))
            pipe.fit(Xtr, ytr, model__sample_weight=balanced_weights(ytr))
            score = pipe.predict_proba(Xte)[:, 1]
        truth = y.loc[test].to_numpy()

        if len(np.unique(truth)) == 2:
            aucs.append(float(roc_auc_score(truth, score)))
            recalls_5.append(recall_at_fpr(truth, score, 0.05))
            recalls_1.append(recall_at_fpr(truth, score, 0.01))
        if held == "S0":
            pred = (score >= 0.5).astype(int)
            tn = int(np.sum((pred == 0) & (truth == 0)))
            fp = int(np.sum((pred == 1) & (truth == 0)))
            spec_s0 = tn / (tn + fp) if (tn + fp) else float("nan")

        if reducer == "pca":
            kept.append(pipe.named_steps["pca"].n_components_)

    n_features = float(np.mean(kept)) if kept else float(X.shape[1])
    return (
        float(np.mean(aucs)),
        spec_s0,
        n_features,
        float(np.mean(recalls_5)),
        float(np.mean(recalls_1)),
    )


def recipe(X: pd.DataFrame, reducer: str) -> pd.DataFrame:
    """Apply the data-independent part of a reducer to a whole feature frame."""
    if reducer in ("dimensionless", "dimensionless_corr"):
        return X[dimensionless_columns(X)]
    if reducer == "physical_corr":
        return physical_features(X)
    if reducer == "avg_dimensionless":
        return average_dimensionless(X)
    return X


def main() -> int:
    warnings.filterwarnings("ignore")
    matrices = build_matrices(load_all())
    X = detrend(matrices.X, matrices.scenario, method="range", window=120)
    y, scenario = matrices.y_binary, matrices.scenario

    rows = []
    for model_name in ("rf", "xgb"):
        for reducer in REDUCERS:
            data = recipe(X, reducer)
            auc, spec, n, rec5, rec1 = _loso(data, y, scenario, model_name, reducer)
            row = {
                "reducer": reducer,
                "model": model_name,
                "n_features": round(n, 1),
                "auc_mean": auc,
                "spec_S0": spec,
                "recall_5": rec5,
                "recall_1": rec1,
            }
            rows.append(row)
            print(row, flush=True)

    result = pd.DataFrame(rows)
    result.to_csv("resultados/reduccion.csv", index=False)
    print("\nwrote resultados/reduccion.csv")
    print(result.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
