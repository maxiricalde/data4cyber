#!/usr/bin/env python3
"""Predicción standalone con el modelo empaquetado en ``modelo_deploy.pkl``.

No necesita el proyecto ni ``src2/``: solo pandas, numpy, scikit-learn y xgboost.
El ``.pkl`` trae los bloques de PCA ya ajustados, el XGBoost, el pipeline Birch,
sus prototipos y el umbral, así que se puede copiar junto a este script a
cualquier máquina.

Uso::

    python deploy_portable.py datos.csv
    python deploy_portable.py datos.csv --pkl modelo_deploy.pkl --salida pred.csv
"""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import pairwise_distances_argmin_min

VENTANA = 120
UMBRAL_XGB = 0.5


def eliminar_columnas(df):
    """Réplica de ``src2.data.eliminar_columnas`` (sin importar el paquete)."""
    df = df.drop(columns=["attack_phase", "attack_phase_all", "timestamp"])
    df = df.drop(columns=[c for c in df.columns if "MQTT-Price-Signal" in c])
    df = df.drop(columns=[c for c in df.columns if "realtime" in c])
    df = df.drop(columns=[c for c in df.columns if "phase_seq" in c])
    df = df.drop(columns=[c for c in df.columns if "Profile" in c])
    return df


def rango_movil(df, ventana=VENTANA):
    """Réplica de ``src2.features.rango_movil``."""
    rodante = df.rolling(ventana, min_periods=1)
    return rodante.max() - rodante.min()


def preprocesar(df, paquete):
    df = eliminar_columnas(df)
    if "attack_active" in df.columns:
        df = df.drop(columns="attack_active")
    for col, media in paquete["medias"].items():
        if col in df.columns:
            df[col] = df[col].fillna(media)
    rango = rango_movil(df, paquete.get("ventana", VENTANA))
    return rango[paquete["columnas"]]


def transformar_bloques(X, bloques):
    """Réplica de ``GroupedPCA.transform``: PCA por bloque y concatenación."""
    partes = []
    for cols, escalador, pca in bloques:
        parte = X[cols].to_numpy()
        if pca is not None:
            parte = pca.transform(escalador.transform(parte))
        partes.append(parte)
    return np.hstack(partes)


def prototipos(modelo, respaldo):
    """Réplica de ``src2.unsupervised.prototipos``."""
    for atributo in ("cluster_centers_", "subcluster_centers_", "components_"):
        if hasattr(modelo, atributo):
            puntos = getattr(modelo, atributo)
            if len(puntos) > 0:
                return puntos
    return respaldo


def predecir(csv_path, pkl_path="modelo_deploy.pkl"):
    """Puntúa un CSV crudo (una fila por segundo) y devuelve un DataFrame."""
    with open(pkl_path, "rb") as f:
        paquete = pickle.load(f)

    X_rango = preprocesar(pd.read_csv(csv_path), paquete)

    proba = paquete["xgb_model"].predict_proba(
        transformar_bloques(X_rango, paquete["pca_blocks"])
    )[:, 1]
    umbral_xgb = float(paquete.get("xgb_umbral", UMBRAL_XGB))
    ataque_xgb = (proba >= umbral_xgb).astype(int)

    Z = paquete["birch_pipe"].transform(X_rango)
    _, score = pairwise_distances_argmin_min(
        Z, prototipos(paquete["birch_model"], paquete["birch_Z"])
    )
    umbral = paquete["birch_umbral"]

    return pd.DataFrame({
        "prob_ataque_xgb": proba,
        "ataque_xgb": ataque_xgb,
        "score_birch": score,
        "flag_birch": (score > umbral).astype(int),
    })


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="CSV crudo (una fila por segundo)")
    ap.add_argument("--pkl", default="modelo_deploy.pkl", help="paquete portable")
    ap.add_argument("--salida", help="CSV donde escribir la predicción")
    args = ap.parse_args()

    pred = predecir(args.csv, args.pkl)
    if args.salida:
        pred.to_csv(args.salida, index=False)
        print(f"escrito {args.salida}: {len(pred)} filas")
    else:
        print(pred.describe().round(3).to_string())
    print(f"xgb:   {int(pred['ataque_xgb'].sum())} ataques / {len(pred)} filas")
    print(f"birch: {int(pred['flag_birch'].sum())} marcadas / {len(pred)} filas")


if __name__ == "__main__":
    main()
