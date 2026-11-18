"""Per-scenario transformations that remove slow drift.

Every transformation here is causal: a row's value depends only on itself and
the rows before it inside the same scenario. It never reads the label and never
reads a future row, so it can be applied before the train/test split without
leaking information.

The methods exist to answer one question: how much of the measured performance
comes from the clock (slow drift and position) and how much survives once the
clock is removed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

METHODS: tuple[str, ...] = ("none", "mean", "zscore", "std", "range", "diff")


def detrend(
    X: pd.DataFrame,
    scenario: pd.Series,
    method: str = "mean",
    window: int = 60,
) -> pd.DataFrame:
    """Return a drift-removed copy of ``X``.

    ``mean``   subtract the trailing rolling mean (a high-pass filter).
    ``zscore`` subtract the mean and divide by the trailing rolling std.
    ``std``    keep only the trailing rolling standard deviation.
    ``range``  keep only the trailing rolling max-minus-min range.
    ``diff``   first difference inside the scenario.

    ``window`` is measured in rows; one row is one second in this dataset. The
    first ``window - 1`` rows of each scenario use a shorter window
    (``min_periods=1``) and are left for the pipeline's median imputation.
    """
    if method not in METHODS:
        raise ValueError(f"unknown detrend method {method!r}; expected one of {METHODS}")
    if method == "none":
        return X
    if method == "diff":
        return X.groupby(scenario).diff().reindex(X.index)

    roll = X.groupby(scenario).rolling(window, min_periods=1)
    if method == "mean":
        out = X - roll.mean().reset_index(level=0, drop=True)
    elif method == "zscore":
        mean = roll.mean().reset_index(level=0, drop=True)
        std = roll.std(ddof=0).reset_index(level=0, drop=True).replace(0, np.nan)
        out = (X - mean) / std
    elif method == "std":
        out = roll.std(ddof=0).reset_index(level=0, drop=True)
    else:  # range
        out = (
            roll.max().reset_index(level=0, drop=True)
            - roll.min().reset_index(level=0, drop=True)
        )
    return out.reindex(X.index)
