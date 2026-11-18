"""Model factories and the shared preprocessing pipeline.

Every experiment fits the same ``Pipeline`` so that imputation, constant-column
removal and scaling are learned from the training fold only.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

SEED = 42
MODEL_NAMES: tuple[str, ...] = ("rf", "svm", "xgb")


def make_model(name: str, seed: int = SEED):
    """Return an unfitted estimator with sensible defaults, no tuning."""
    if name == "rf":
        return RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=seed,
        )
    if name == "svm":
        return SVC(
            kernel="rbf",
            C=1.0,
            gamma="scale",
            cache_size=1000,
            random_state=seed,
        )
    if name == "xgb":
        return XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            tree_method="hist",
            eval_metric="logloss",
            n_jobs=-1,
            random_state=seed,
        )
    raise ValueError(f"unknown model {name!r}; expected one of {MODEL_NAMES}")


def build_pipeline(model) -> Pipeline:
    """Impute -> drop constants -> scale -> model, fitted as one unit per fold."""
    return Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median", add_indicator=False)),
            ("variance", VarianceThreshold(0.0)),
            ("scale", StandardScaler()),
            ("model", model),
        ]
    )


def balanced_weights(y) -> np.ndarray:
    """Inverse-frequency sample weights, so every class contributes equally."""
    y = np.asarray(y)
    classes, counts = np.unique(y, return_counts=True)
    if len(classes) < 2:
        return np.ones(len(y))
    per_class = {cls: len(y) / (len(classes) * count) for cls, count in zip(classes, counts)}
    return np.array([per_class[value] for value in y])
