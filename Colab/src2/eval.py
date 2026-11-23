"""Validación supervisada: leave-one-scenario-out con métricas por fold."""

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)


def loso(dfsX, dfsY, modelo):
    """Un fold por escenario; devuelve la tabla por escenario y las predicciones.

    El modelo se clona y se ajusta en cada fold, así que nunca ve el escenario
    que tiene que predecir. Devuelve `(tabla, (y_true, y_pred, y_proba))`, con
    las tres series concatenadas en el orden en que se recorren los escenarios.
    """
    filas = []
    y_true, y_pred, y_proba = [], [], []

    for test in dfsX:
        otros = [k for k in dfsX if k != test]
        X_train = pd.concat([dfsX[k] for k in otros], ignore_index=True)
        y_train = pd.concat([dfsY[k] for k in otros], ignore_index=True)

        ajustado = clone(modelo).fit(X_train, y_train)
        proba = ajustado.predict_proba(dfsX[test].reset_index(drop=True))[:, 1]
        y_test = dfsY[test].to_numpy()
        pred = (proba >= 0.5).astype(int)

        filas.append({
            "escenario": test,
            "n": len(y_test),
            "positivos": int(y_test.sum()),
            "accuracy": accuracy_score(y_test, pred),
            "precision": precision_score(y_test, pred, zero_division=0),
            "recall": recall_score(y_test, pred, zero_division=0),
            "f1": f1_score(y_test, pred, zero_division=0),
            # S0 no tiene positivos: ahí el AUC no está definido.
            "auc": roc_auc_score(y_test, proba) if len(np.unique(y_test)) > 1 else np.nan,
        })
        y_true.append(y_test)
        y_pred.append(pred)
        y_proba.append(proba)

    tabla = pd.DataFrame(filas).set_index("escenario")
    return tabla, (np.concatenate(y_true), np.concatenate(y_pred), np.concatenate(y_proba))
