

import pandas as pd


def tabla_nulos(df):
    """Columnas con nulos, de mayor a menor, con el porcentaje sobre las filas."""
    nulos = df.isna().sum()
    tabla = pd.DataFrame({"nulos": nulos, "pct": (100 * nulos / len(df)).round(2)})
    return tabla[tabla["nulos"] > 0].sort_values("nulos", ascending=False)
