#!/usr/bin/env python3
"""Motor de inferencia desacoplado.

Importa dinámicamente cualquier script de deploy (supervisado, nosupervisado,
regímenes), carga su .pkl y corre la predicción sobre el CSV completo.

Puede usarse como módulo (desde app.py) o standalone:

    python inferencia.py --script ../deploy_supervisado.py \
                         --pkl modelos/supervisado.pkl \
                         --csv data/datas.csv
"""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- loader ----

def _importar_script(script_path: str):
    """Importa dinámicamente un .py de deploy y devuelve el módulo."""
    path = Path(script_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Script no encontrado: {path}")
    spec = importlib.util.spec_from_file_location("deploy_module", str(path))
    mod = importlib.util.module_from_spec(spec)
    # Agregar el directorio del script al path para imports relativos
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    spec.loader.exec_module(mod)
    return mod


def _buscar_funciones(mod):
    """Encuentra cargar_paquete y predecir_* en el módulo."""
    cargar = getattr(mod, "cargar_paquete", None)
    if cargar is None:
        raise AttributeError("El script no tiene función 'cargar_paquete'")

    predecir = None
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("predecir_"):
            predecir = obj
            break
    if predecir is None:
        raise AttributeError("El script no tiene función 'predecir_*'")

    return cargar, predecir


# ---------------------------------------------------------------- infer ----

def _serializar_valor(val):
    """Convierte un valor numpy/pandas a tipo nativo de Python."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, (np.integer, np.bool_)):
        return int(val)
    if isinstance(val, np.floating):
        return round(float(val), 4)
    if isinstance(val, (int, float, bool)):
        return val
    return str(val)


def ejecutar_inferencia(script_path: str, pkl_path: str, csv_path: str) -> list[dict]:
    """Corre el pipeline completo y devuelve una lista de dicts normalizados.

    Cada dict tiene al menos: idx, timestamp, score, flag, ground_truth.
    """
    mod = _importar_script(script_path)
    cargar, predecir = _buscar_funciones(mod)

    paquete = cargar(pkl_path)
    df_raw = pd.read_csv(csv_path)

    # Metadatos del CSV original
    timestamps = (df_raw["timestamp"].values if "timestamp" in df_raw.columns
                  else [f"T+{i}s" for i in range(len(df_raw))])
    has_gt = "attack_active" in df_raw.columns
    gt = df_raw["attack_active"].values if has_gt else [None] * len(df_raw)

    # Predicción completa (necesita el DF entero por rolling window / invariantes)
    result_df = predecir(df_raw, paquete)
    cols = result_df.columns.tolist()

    # Detectar columnas de score y flag según el modelo
    score_col, flag_col = None, None
    for c in cols:
        if "prob" in c.lower() or "score" in c.lower():
            score_col = c
        if "ataque" in c.lower() or "flag" in c.lower():
            flag_col = c

    resultados = []
    for i in range(len(result_df)):
        row = {
            "idx": i,
            "timestamp": str(timestamps[i]),
        }

        # Agregar todas las columnas originales del modelo
        for c in cols:
            row[c] = _serializar_valor(result_df.iloc[i][c])

        # Normalizar a schema común
        row["score"] = _serializar_valor(result_df.iloc[i][score_col]) if score_col else None
        row["flag"] = int(result_df.iloc[i][flag_col]) if flag_col else None
        row["ground_truth"] = bool(gt[i]) if gt[i] is not None else None

        resultados.append(row)

    return resultados


# ------------------------------------------------------------------ cli ----

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", required=True, help="Path al .py de deploy")
    ap.add_argument("--pkl", required=True, help="Path al .pkl del modelo")
    ap.add_argument("--csv", default="data/datas.csv", help="Path al CSV de datos")
    ap.add_argument("--output", default="resultados.jsonl", help="Archivo JSONL de salida")
    args = ap.parse_args()

    print(f"Cargando script: {args.script}")
    print(f"Cargando modelo: {args.pkl}")
    print(f"Leyendo datos:   {args.csv}")

    resultados = ejecutar_inferencia(args.script, args.pkl, args.csv)

    with open(args.output, "w") as f:
        for r in resultados:
            f.write(json.dumps(r) + "\n")

    n_flags = sum(1 for r in resultados if r.get("flag") == 1)
    print(f"Escritos {len(resultados)} resultados en {args.output}")
    print(f"  Flagged: {n_flags} / {len(resultados)}")


if __name__ == "__main__":
    main()
