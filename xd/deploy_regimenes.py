#!/usr/bin/env python3
"""Etiquetador de régimen NO SUPERVISADO (KMeans sobre invariantes físicas).

No detecta ataques: asigna cada fila a un régimen de operación y devuelve la
etiqueta (texto), no un score ni un flag.

El .pkl trae las columnas invariantes, el pipeline de preproceso, los centroides
KMeans y el mapa cluster -> etiqueta.

Uso::

    python deploy_regimenes.py datos.csv                       # resumen por pantalla
    python deploy_regimenes.py datos.csv --salida pred.csv      # etiqueta por fila
"""
from __future__ import annotations

import argparse
import pickle

import numpy as np
import pandas as pd
from sklearn.metrics import pairwise_distances_argmin_min

MEDIDORES = ["BSS-Inverter-AC-Meter", "Load-A-AC-Meter", "Load-B-AC-Meter",
             "PV-Inverter-AC-Meter", "Substation-AC-Meter"]
RAMAS = [m for m in MEDIDORES if m != "Substation-AC-Meter"]


# ---------------------------------------------------------------- runtime ----

def cargar_paquete(pkl_path: str = "deploy_regimenes.pkl") -> dict:
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def invariantes_fisicas(df: pd.DataFrame) -> pd.DataFrame:
    """Invariantes intra-medidor (ΔSOC, S_error, imbalance) + balance nodal (P, Q)."""
    inv = pd.DataFrame(index=df.index)
    inv["dsoc"] = (df["Battery-SOC-Reported.soc_value"]
                   - df["Battery-SOC-Reference.soc_value"]).abs()
    for medidor in MEDIDORES:
        p = df[f"{medidor}.p_sum3"]
        q = df[f"{medidor}.q_sum3"]
        s = df[f"{medidor}.s_sum3"]
        inv[f"{medidor}__serror"] = np.sqrt(p**2 + q**2) - s
        fases = [df[f"{medidor}.uln1"], df[f"{medidor}.uln2"], df[f"{medidor}.uln3"]]
        pares = [(fases[i] - fases[j]).abs() for i in range(3) for j in range(i + 1, 3)]
        inv[f"{medidor}__imbalance"] = pd.concat(pares, axis=1).max(axis=1)
    inv["balance_p"] = (df["Substation-AC-Meter.p_sum3"]
                        - sum(df[f"{m}.p_sum3"] for m in RAMAS))
    inv["balance_q"] = (df["Substation-AC-Meter.q_sum3"]
                        - sum(df[f"{m}.q_sum3"] for m in RAMAS))
    return inv


def predecir_regimen(df: pd.DataFrame, paquete: dict) -> pd.DataFrame:
    """Asigna a cada fila la etiqueta del centroide KMeans más cercano."""
    X_inv = invariantes_fisicas(df)[paquete["columnas_invariantes"]]
    Z = paquete["pipeline"].transform(X_inv)
    indice, _ = pairwise_distances_argmin_min(Z, paquete["kmeans_centroides"])
    etiquetas = paquete["etiquetas"]
    return pd.DataFrame({"regimen": [etiquetas[int(i)] for i in indice]})


# -------------------------------------------------------------------- cli ----

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="CSV crudo (una fila por segundo)")
    ap.add_argument("--pkl", default="deploy_regimenes.pkl", help="paquete portable")
    ap.add_argument("--salida", help="CSV donde escribir la etiqueta por fila")
    args = ap.parse_args()

    paquete = cargar_paquete(args.pkl)
    pred = predecir_regimen(pd.read_csv(args.csv), paquete)

    if args.salida:
        pred.to_csv(args.salida, index=False)
        print(f"escrito {args.salida}: {len(pred)} filas")
    print(pred["regimen"].value_counts().to_string())


if __name__ == "__main__":
    main()
