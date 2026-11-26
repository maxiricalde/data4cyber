#!/usr/bin/env python3
"""Predicción NO SUPERVISADA standalone (Birch + invariantes físicos).

Runtime: no necesita el proyecto ni src2/. Solo pandas, numpy y scikit-learn.
El .pkl trae las columnas invariantes, el pipeline de preproceso, los prototipos
Birch y el umbral calibrado.

Uso::

    python deploy_nosupervisado.py datos.csv                    # predice
    python deploy_nosupervisado.py datos.csv --salida pred.csv   # predice -> CSV
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

def cargar_paquete(pkl_path: str = "deploy_nosupervisado.pkl") -> dict:
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


def predecir_no_supervisado(df: pd.DataFrame, paquete: dict) -> pd.DataFrame:
    """Puntúa filas crudas con la distancia al prototipo benigno más cercano."""
    X_inv = invariantes_fisicas(df)[paquete["columnas_invariantes"]]
    Z = paquete["pipeline"].transform(X_inv)
    _, score = pairwise_distances_argmin_min(Z, paquete["birch_prototipos"])
    umbral = float(paquete["birch_umbral"])
    return pd.DataFrame({
        "score_birch": score,
        "flag_birch": (score > umbral).astype(int),
    })


# -------------------------------------------------------------------- cli ----

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="CSV crudo (una fila por segundo)")
    ap.add_argument("--pkl", default="deploy_nosupervisado.pkl", help="paquete portable")
    ap.add_argument("--salida", help="CSV donde escribir la predicción")
    args = ap.parse_args()

    paquete = cargar_paquete(args.pkl)
    pred = predecir_no_supervisado(pd.read_csv(args.csv), paquete)

    if args.salida:
        pred.to_csv(args.salida, index=False)
        print(f"escrito {args.salida}: {len(pred)} filas")
    else:
        print(pred.describe().round(3).to_string())
    print(f"birch: {int(pred['flag_birch'].sum())} marcadas / {len(pred)} filas")


if __name__ == "__main__":
    main()
