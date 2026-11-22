"""Paquete de producción: el reductor ajustado más el modelo."""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from .train import PARAMS_RF


def entrenar_final(dfsX, dfsY, reductor=None):
    """Entrena con todos los escenarios y devuelve el paquete reductor + modelo."""
    X_train = pd.concat([dfsX[k] for k in dfsX], ignore_index=True)
    y_train = pd.concat([dfsY[k] for k in dfsX], ignore_index=True)

    if reductor is None:
        ajustado = None
        X_modelo = X_train.to_numpy()
    else:
        ajustado = reductor().fit(X_train)
        X_modelo = ajustado.transform(X_train)

    modelo = RandomForestClassifier(**PARAMS_RF).fit(X_modelo, y_train)
    return {"reductor": ajustado, "modelo": modelo}


def predecir(paquete, X):
    """Score de ataque para filas nuevas, con la transformación aprendida en el entrenamiento."""
    X_modelo = X.to_numpy() if paquete["reductor"] is None else paquete["reductor"].transform(X)
    return paquete["modelo"].predict_proba(X_modelo)[:, 1]
