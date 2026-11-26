

import pandas as pd


def rango_movil(df, ventana=120):
    rodante = df.rolling(ventana, min_periods=1)
    return rodante.max() - rodante.min()


def rango_escenarios(dfs, ventana=120):
    """Aplica `rango_movil` escenario por escenario"""
    return {k: rango_movil(df, ventana) for k, df in dfs.items()}

def rango_por_escenario(X):
    """Rango móvil de 120 s, escenario por escenario."""
    partes = []
    for k in X["escenario"].unique():
        bloque = X.loc[X["escenario"] == k].drop(columns="escenario")
        partes.append(rango_movil(bloque, 120))
    return pd.concat(partes, ignore_index=True)
