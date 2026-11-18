"""Window sweep: how much clock survives each drift-removal choice.

For every (method, window) pair this reports three numbers:

- ``mean_abs_rho``: mean |Spearman| between each transformed feature and the
  relative position inside its scenario. The cheap proxy for "how much clock
  is left".
- ``auc_mean``: mean LOSO AUC over the seven attack folds. A Random Forest with
  150 trees is used instead of the 300-tree main model to keep the sweep under
  ten minutes; the relative ordering is what matters here.
- ``spec_S0``: specificity on the unseen benign S0 fold at the default 0.5
  threshold. This is the number that decides usability.

Run with: python -m src.sweep
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

from .data import SCENARIOS, build_matrices, load_all
from .features import detrend
from .pipeline import balanced_weights, build_pipeline

WINDOWS: tuple[int, ...] = (5, 15, 30, 60, 120, 300)
METHODS: tuple[str, ...] = ("mean", "zscore", "std", "range")
SEED = 42


def _sweep_model():
    return RandomForestClassifier(
        n_estimators=150,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=SEED,
    )


def clock_correlation(X: pd.DataFrame, position: pd.Series) -> tuple[float, float]:
    """Mean and max |Spearman| between the features and the relative position."""
    pos = position.to_numpy(dtype=float)
    rhos = []
    for column in X.columns:
        values = X[column].to_numpy(dtype=float)
        mask = np.isfinite(values) & np.isfinite(pos)
        if mask.sum() < 100 or np.std(values[mask]) == 0:
            continue
        rho, _ = spearmanr(values[mask], pos[mask])
        if np.isfinite(rho):
            rhos.append(abs(rho))
    return float(np.mean(rhos)), float(np.max(rhos))


def loso_scores(X: pd.DataFrame, y: pd.Series, scenario: pd.Series) -> tuple[float, float]:
    """Mean AUC over the attack folds and specificity on the S0 fold."""
    aucs = []
    spec_s0 = float("nan")
    for held in SCENARIOS:
        test = (scenario == held).to_numpy()
        train = ~test
        pipe = build_pipeline(_sweep_model())
        pipe.fit(
            X.loc[train],
            y.loc[train],
            model__sample_weight=balanced_weights(y.loc[train]),
        )
        score = pipe.predict_proba(X.loc[test])[:, 1]
        truth = y.loc[test].to_numpy()

        if len(np.unique(truth)) == 2:
            aucs.append(float(roc_auc_score(truth, score)))
        if held == "S0":
            pred = (score >= 0.5).astype(int)
            tn = int(np.sum((pred == 0) & (truth == 0)))
            fp = int(np.sum((pred == 1) & (truth == 0)))
            spec_s0 = tn / (tn + fp) if (tn + fp) else float("nan")
    return float(np.mean(aucs)), spec_s0


def _row(method: str, window: float, X, y, scenario, position) -> dict:
    rho_mean, rho_max = clock_correlation(X, position)
    auc, spec = loso_scores(X, y, scenario)
    return {
        "method": method,
        "window": window,
        "mean_abs_rho": rho_mean,
        "max_abs_rho": rho_max,
        "auc_mean": auc,
        "spec_S0": spec,
    }


def main() -> int:
    warnings.filterwarnings("ignore")
    matrices = build_matrices(load_all())
    y, scenario, position = matrices.y_binary, matrices.scenario, matrices.position

    rows = [_row("none", np.nan, matrices.X, y, scenario, position)]
    print(rows[-1], flush=True)

    for method in METHODS:
        for window in WINDOWS:
            X = detrend(matrices.X, scenario, method=method, window=window)
            rows.append(_row(method, window, X, y, scenario, position))
            print(rows[-1], flush=True)

    X = detrend(matrices.X, scenario, method="diff")
    rows.append(_row("diff", np.nan, X, y, scenario, position))
    print(rows[-1], flush=True)

    result = pd.DataFrame(rows)
    result.to_csv("resultados/barrido_ventana.csv", index=False)
    print("\nwrote resultados/barrido_ventana.csv")
    print(result.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
