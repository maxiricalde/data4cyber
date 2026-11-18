"""Physics-only detector: three-phase power balance residual.

Each meter reports the power of every phase (``pln1..3``) and a total
(``p_sum3``), and the same for reactive and apparent power. In a healthy meter
the total equals the sum of its phases up to measurement noise. During the ARP
attacks the reported phases and the total disagree far beyond that noise: the
manipulated frames do not respect the balance the meter itself measures.

The score of a row is the largest relative residual over the five meters and
the three quantities. The threshold is a quantile of the benign scores, so the
rule needs no labels and no attack examples; it is complementary to the
learned detector and only covers the ARP family, which is the one that tampers
with the meter readings.

Run with: python -m src.physics
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from .data import SCENARIOS, build_matrices, load_all

METERS: tuple[str, ...] = (
    "BSS-Inverter-AC-Meter",
    "PV-Inverter-AC-Meter",
    "Load-A-AC-Meter",
    "Load-B-AC-Meter",
    "Substation-AC-Meter",
)
QUANTITIES: tuple[str, ...] = ("p", "q", "s")
FLOOR: float = 1.0  # kW; keeps the ratio stable when a total is near zero


def _relative_residual(X: pd.DataFrame, meter: str, quantity: str) -> pd.Series:
    """|total - sum(phases)| over |total| + floor, NaN when a phase is missing."""
    total = X[f"{meter}.{quantity}_sum3"]
    phases = X[[f"{meter}.{quantity}ln{i}" for i in (1, 2, 3)]].sum(
        axis=1, skipna=False
    )
    return ((total - phases).abs() / (total.abs() + FLOOR)).fillna(0.0)


def residuals(X: pd.DataFrame) -> pd.DataFrame:
    """Relative phase-balance residual per meter and quantity."""
    return pd.DataFrame(
        {
            f"{meter.replace('-AC-Meter', '')}.{quantity}": _relative_residual(
                X, meter, quantity
            )
            for meter in METERS
            for quantity in QUANTITIES
        }
    )


def score(X: pd.DataFrame) -> pd.Series:
    """Largest relative residual of the row: one number per timestamp."""
    return residuals(X).max(axis=1)


def fit_threshold(scores: pd.Series, fpr: float = 0.05) -> float:
    """Benign-only threshold that flags the given fraction of benign rows."""
    return float(scores.quantile(1.0 - fpr))


def run(fpr: float = 0.05) -> pd.DataFrame:
    matrices = build_matrices(load_all())
    X = matrices.X
    y = matrices.y_binary
    scenario = matrices.scenario
    scores = score(X)

    rows = []
    for held in SCENARIOS:
        test = (scenario == held).to_numpy()
        benign_train = (~test) & (y == 0).to_numpy()
        threshold = fit_threshold(scores[benign_train], fpr)
        flag = (scores > threshold).to_numpy()

        attack = test & (y == 1).to_numpy()
        benign = test & (y == 0).to_numpy()
        tpr = float(flag[attack].mean()) if attack.any() else np.nan
        false_alarm = float(flag[benign].mean()) if benign.any() else np.nan
        auc = np.nan
        if attack.any() and benign.any():
            from sklearn.metrics import roc_auc_score

            auc = float(
                roc_auc_score(
                    np.r_[np.zeros(benign.sum()), np.ones(attack.sum())],
                    np.r_[scores.to_numpy()[benign], scores.to_numpy()[attack]],
                )
            )
        rows.append(
            {
                "fold": held,
                "threshold": threshold,
                "tpr": tpr,
                "fpr": false_alarm,
                "auc": auc,
                "n_attack": int(attack.sum()),
                "n_benign": int(benign.sum()),
            }
        )
        print(f"  {held:6s} threshold={threshold:.4f}", flush=True)

    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fpr", type=float, default=0.05)
    parser.add_argument("--out", default="resultados/fisica.csv")
    args = parser.parse_args()

    result = run(args.fpr)
    result.to_csv(args.out, index=False)

    print("\nDetector físico, LOSO")
    print(result[["fold", "tpr", "fpr", "auc"]].round(3).to_string(index=False))
    arp = result[result["fold"].isin(["S3", "S4", "S5"])]
    print(f"\nTPR medio ARP: {arp['tpr'].mean():.3f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
