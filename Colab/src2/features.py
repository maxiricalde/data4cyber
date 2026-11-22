"""Transformaciones por escenario. Una fila es un segundo."""

import pandas as pd


def rango_movil(df, ventana=120):
    rodante = df.rolling(ventana, min_periods=1)
    return rodante.max() - rodante.min()


def rango_escenarios(dfs, ventana=120):
    """Aplica `rango_movil` escenario por escenario"""
    return {k: rango_movil(df, ventana) for k, df in dfs.items()}
