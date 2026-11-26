#!/usr/bin/env python3
"""Predicción SUPERVISADA standalone (solo XGBoost + GroupedPCA ya ajustado).

Runtime: no necesita el proyecto ni src2/. Solo pandas, numpy, scikit-learn y
xgboost. El .pkl trae columnas, medias de imputación, ventana, el XGBoost y los
bloques PCA.

Uso::

    python deploy_supervisado.py datos.csv                    # predice
    python deploy_supervisado.py datos.csv --salida pred.csv   # predice -> CSV
"""
from __future__ import annotations

import argparse
import pickle

import numpy as np
import pandas as pd

VENTANA = 120
UMBRAL_XGB = 0.5


# ---------------------------------------------------------------- runtime ----

def cargar_paquete(pkl_path: str = "modelo_supervisado.pkl") -> dict:
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def eliminar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop(columns=["attack_phase", "attack_phase_all", "timestamp"])
    df = df.drop(columns=[c for c in df.columns if "MQTT-Price-Signal" in c])
    df = df.drop(columns=[c for c in df.columns if "realtime" in c])
    df = df.drop(columns=[c for c in df.columns if "phase_seq" in c])
    df = df.drop(columns=[c for c in df.columns if "Profile" in c])
    return df


def rango_movil(df: pd.DataFrame, ventana: int = VENTANA) -> pd.DataFrame:
    rodante = df.rolling(ventana, min_periods=1)
    return rodante.max() - rodante.min()


def preprocesar(df: pd.DataFrame, paquete: dict) -> pd.DataFrame:
    df = eliminar_columnas(df)
    if "attack_active" in df.columns:
        df = df.drop(columns="attack_active")
    for col, media in paquete["medias"].items():
        if col in df.columns:
            df[col] = df[col].fillna(media)
    rango = rango_movil(df, paquete.get("ventana", VENTANA))
    return rango[paquete["columnas"]]


def transformar_bloques(X: pd.DataFrame, bloques) -> np.ndarray:
    partes = []
    for cols, escalador, pca in bloques:
        parte = X[cols].to_numpy()
        if pca is not None:
            parte = pca.transform(escalador.transform(parte))
        partes.append(parte)
    return np.hstack(partes)


def predecir_supervisado(df: pd.DataFrame, paquete: dict) -> pd.DataFrame:
    """Puntúa filas crudas (una por segundo). La última fila usa la ventana previa."""
    X_rango = preprocesar(df, paquete)
    proba = paquete["xgb_model"].predict_proba(
        transformar_bloques(X_rango, paquete["pca_blocks"])
    )[:, 1]
    umbral = float(paquete.get("xgb_umbral", UMBRAL_XGB))
    return pd.DataFrame({
        "prob_ataque_xgb": proba,
        "ataque_xgb": (proba >= umbral).astype(int),
    })


# -------------------------------------------------------------------- cli ----

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="CSV crudo (una fila por segundo)")
    ap.add_argument("--pkl", default="modelo_supervisado.pkl", help="paquete portable")
    ap.add_argument("--salida", help="CSV donde escribir la predicción")
    args = ap.parse_args()

    paquete = cargar_paquete(args.pkl)
    pred = predecir_supervisado(pd.read_csv(args.csv), paquete)

    if args.salida:
        pred.to_csv(args.salida, index=False)
        print(f"escrito {args.salida}: {len(pred)} filas")
    else:
        print(pred.describe().round(3).to_string())
    print(f"xgb: {int(pred['ataque_xgb'].sum())} ataques / {len(pred)} filas")


if __name__ == "__main__":
    main()
