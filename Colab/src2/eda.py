"""Helpers del EDA: rango por escenario, primer ataque sostenido y tabla de nulos."""

import pandas as pd

from .features import rango_escenarios


def rango_movil_escenarios(dfs, ventana=120):
    """Rango móvil de `ventana` segundos, escenario por escenario."""
    return rango_escenarios(dfs, ventana)


def primer_ataque_sostenido(etiquetas, minimo=60):
    """Posición del primer ataque que dura al menos `minimo` filas seguidas."""
    racha = 0
    for i, valor in enumerate(etiquetas):
        racha = racha + 1 if valor else 0
        if racha >= minimo:
            return i - minimo + 1
    return None


def tabla_nulos(df):
    """Columnas con nulos, de mayor a menor, con el porcentaje sobre las filas."""
    nulos = df.isna().sum()
    tabla = pd.DataFrame({"nulos": nulos, "pct": (100 * nulos / len(df)).round(2)})
    return tabla[tabla["nulos"] > 0].sort_values("nulos", ascending=False)
