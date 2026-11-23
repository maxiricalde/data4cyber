"""Modelos y evaluación del supervisado: LOSO y métricas."""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score,
                             roc_curve)
from sklearn.model_selection import LeaveOneGroupOut

SEED = 42

PARAMS_RF = {
    "n_estimators": 120,
    "max_depth": 18,
    "min_samples_leaf": 2,
    "class_weight": "balanced",
    "random_state": SEED,
    "n_jobs": -1,
}

PARAMS_XGB = {
    "n_estimators": 300,
    "max_depth": 4,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "tree_method": "hist",
    "eval_metric": "logloss",
    "random_state": SEED,
    "n_jobs": -1,
}


def recall_5(y_true, score, fpr=0.05):
    """TPR al 5 % de falsos positivos, leído de la curva ROC.

    No depende de un umbral fijo: mide qué fracción de los ataques entra en la
    banda de mayor score que el operador toleraría.
    """
    f, t, _ = roc_curve(y_true, score)
    return float(np.interp(fpr, f, t))


def _metricas(y_true, proba):
    """Las métricas de siempre, con umbral 0.5 y con recall@5."""
    pred = (proba >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "n": len(y_true),
        "positivos": int(y_true.sum()),
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "especificidad": tn / (tn + fp) if (tn + fp) else np.nan,
        "auc": roc_auc_score(y_true, proba) if len(np.unique(y_true)) > 1 else np.nan,
        "recall_5": recall_5(y_true, proba) if len(np.unique(y_true)) > 1 else np.nan,
    }


def rf_logo(X, y, grupos):
    """Random Forest con LeaveOneGroupOut, sin reducción."""

    y = np.asarray(y).ravel()
    grupos = np.asarray(grupos)

    filas = []
    for fold, (tr, te) in enumerate(
            LeaveOneGroupOut().split(X, y, groups=grupos), start=1):
        rf = RandomForestClassifier(**PARAMS_RF).fit(X.iloc[tr], y[tr])
        proba = rf.predict_proba(X.iloc[te])[:, 1]

        fila = {"fold": fold, "escenario": grupos[te][0], "features": X.shape[1]}
        fila["accuracy_train"] = rf.score(X.iloc[tr], y[tr])
        fila.update(_metricas(y[te], proba))
        filas.append(fila)

    tabla = pd.DataFrame(filas).set_index("fold").round(3)
    tabla.loc["mean"] = tabla.mean(numeric_only=True).round(3)
    return tabla
