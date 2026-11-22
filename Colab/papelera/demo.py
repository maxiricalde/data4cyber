"""Prueba rápida de las funciones del supervisado: python demo.py

Las funciones vive en `src2/train.py`, `src2/reduce.py` y `src2/production.py`.
Este archivo solo las corre sobre los datos para mirar la tabla de reducciones.
"""

from pathlib import Path

import pandas as pd

from src2.data import eliminar_columnas
from src2.features import rango_escenarios
from Colab.papelera.reduce import REDUCTORES
from src2.split import separar_variables
from src2.train import especificidad_s0, rf_LOSO, resumen_configuraciones

ARCHIVOS = {
    "S1": "datasetS1.csv", "S1alt": "datasetS1alt.csv", "S2": "datasetS2.csv",
    "S3": "datasetS3.csv", "S4": "datasetS4.csv", "S5": "datasetS5.csv",
    "S6": "datasetS6.csv",
}


def main():
    base = Path(__file__).parent.parent / "datasets"

    dfs = {k: eliminar_columnas(pd.read_csv(base / f)) for k, f in ARCHIVOS.items()}
    X, Y = {}, {}
    for k, df in dfs.items():
        X[k], Y[k] = separar_variables(df)

    X_rango = rango_escenarios(X)
    X_s0, _ = separar_variables(eliminar_columnas(pd.read_csv(base / "datasetS0.csv")))
    X_s0_rango = rango_escenarios({"S0": X_s0})["S0"]

    tablas, especificidades = {}, {}
    for nombre, reductor in REDUCTORES.items():
        tablas[nombre] = rf_LOSO(X_rango, Y, reductor)
        especificidades[nombre] = especificidad_s0(X_rango, Y, X_s0_rango, reductor=reductor)

    print("\nreducciones sobre el rango")
    print(resumen_configuraciones(tablas, especificidades).to_string())


if __name__ == "__main__":
    main()
