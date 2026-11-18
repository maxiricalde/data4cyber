"""Partial-effect feature selection: keep the features whose attack signal is not the clock.

For each feature, residualize it on the relative position inside its scenario, then
measure the standardized attack-minus-benign difference (Cohen's d) on the residual.
A feature whose effect disappears after removing position was a clock. The ranking is
computed on the training folds only; the test fold never contributes labels.

Run with: python -m src.select
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from .data import SCENARIOS, build_matrices, load_all
from .pipeline import balanced_weights, build_pipeline, make_model
from .train import binary_report

KS: tuple[int, ...] = (10, 20, 40, 60, 139)
MODELS: tuple[str, ...] = ("rf", "xgb")


def _residualize(X: pd.DataFrame, scenario: pd.Series, position: pd.Series) -> pd.DataFrame:
    """Remove the linear position trend of each feature inside each scenario."""
    out = pd.DataFrame(index=X.index, columns=X.columns, dtype=float)
    for name in SCENARIOS:
        mask = (scenario == name).to_numpy()
        pos = position[mask].to_numpy(dtype=float)
        design = np.column_stack([np.ones(mask.sum()), pos])
        for column in X.columns:
            values = X.loc[mask, column].to_numpy(dtype=float)
            valid = np.isfinite(values) & np.isfinite(pos)
            if valid.sum() < 10:
                out.loc[mask, column] = np.nan
                continue
            coef, *_ = np.linalg.lstsq(design[valid], values[valid], rcond=None)
            out.loc[mask, column] = values - design @ coef
    return out


def _cohens_d(residuals: pd.DataFrame, y: pd.Series, train_mask: np.ndarray) -> pd.Series:
    """Standardized attack-minus-benign difference on the residuals."""
    attack = train_mask & (y == 1).to_numpy()
    benign = train_mask & (y == 0).to_numpy()
    effects = {}
    for column in residuals.columns:
        a = residuals.loc[attack, column].dropna()
        b = residuals.loc[benign, column].dropna()
        if len(a) < 10 or len(b) < 10:
            effects[column] = 0.0
            continue
        pooled = np.sqrt(
            ((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
            / (len(a) + len(b) - 2)
        )
        effects[column] = float((a.mean() - b.mean()) / pooled) if pooled > 0 else 0.0
    return pd.Series(effects)


def run(ks: tuple[int, ...] = KS, models: tuple[str, ...] = MODELS) -> pd.DataFrame:
    warnings.filterwarnings("ignore")
    matrices = build_matrices(load_all())
    X = matrices.X
    y = matrices.y_binary
    scenario = matrices.scenario
    residuals = _residualize(X, scenario, matrices.position)

    rows = []
    for held in SCENARIOS:
        test = (scenario == held).to_numpy()
        train = ~test
        ranking = _cohens_d(residuals, y, train).abs().sort_values(ascending=False).index

        for k in ks:
            columns = list(ranking[:k])
            for model_name in models:
                pipe = build_pipeline(make_model(model_name))
                pipe.fit(
                    X.loc[train, columns],
                    y.loc[train],
                    model__sample_weight=balanced_weights(y.loc[train]),
                )
                score = pipe.predict_proba(X.loc[test, columns])[:, 1]
                report = binary_report(
                    y.loc[test], (score >= 0.5).astype(int), score
                )
                rows.append(
                    {"fold": held, "k": k, "model": model_name, **report}
                )
        print(f"  {held:6s} ranked and evaluated", flush=True)

    return pd.DataFrame(rows)


def main() -> int:
    result = run()
    result.to_csv("resultados/seleccion_parcial.csv", index=False)

    attack = result[result["fold"] != "S0"]
    s0 = result[result["fold"] == "S0"]
    auc = attack.groupby(["model", "k"])["roc_auc"].mean().unstack()
    specificity = s0.groupby(["model", "k"])["specificity"].mean().unstack()

    print("\nAUC media (folds de ataque)")
    print(auc.round(3).to_string())
    print("\nEspecificidad S0")
    print(specificity.round(3).to_string())
    print("\nwrote resultados/seleccion_parcial.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
