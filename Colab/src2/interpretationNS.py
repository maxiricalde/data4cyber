

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score,
                             davies_bouldin_score, normalized_mutual_info_score,
                             silhouette_score)


def zscore_columnas(valores):
    
    valores = np.asarray(valores, dtype=float)
    media = np.nanmean(valores, axis=0)
    desvio = np.nanstd(valores, axis=0)
    desvio[desvio == 0] = 1.0
    return (valores - media) / desvio


def nombre_legible(variable):
    """Traduce el nombre interno de un invariante a algo legible."""
    if variable == "dsoc":
        return "ΔSOC (reportado vs referencia)"
    medidor, _, tipo = variable.partition("__")
    etiqueta = {"serror": "residuo de potencia aparente",
                "imbalance": "desequilibrio de fase"}.get(tipo)
    if not etiqueta:
        return variable
    return f"{medidor} · {etiqueta}"


def perfil_clusters(valores, etiquetas, columnas, top=3, min_peso=0.01):
    
    etiquetas = np.asarray(etiquetas)
    Z = zscore_columnas(valores)

    filas = []
    for c in np.unique(etiquetas):
        en_cluster = etiquetas == c
        peso = float(en_cluster.mean())
        if c == -1 or peso < min_peso:
            continue
        z = np.nanmean(Z[en_cluster], axis=0)
        for j in np.argsort(-np.abs(z))[:top]:
            filas.append({
                "cluster": c,
                "n": int(en_cluster.sum()),
                "peso": round(peso, 3),
                "variable": nombre_legible(str(columnas[j])),
                "z": round(float(z[j]), 1),
            })
    return pd.DataFrame(filas)


def tabla_clusters_escenario(etiquetas, grupos, nombre_grupo="escenario"):
    """Conteo de filas por cluster y grupo (por defecto, escenario)."""
    return pd.crosstab(
        pd.Series(np.asarray(etiquetas), name="cluster"),
        pd.Series(np.asarray(grupos), name=nombre_grupo),
    )


def resumen_clustering(Z, etiquetas, y, grupos, nombre_y="y",
                       nombre_grupo="grupo", random_state=42):
    etiquetas = np.asarray(etiquetas)
    varios = len(np.unique(etiquetas)) > 1
    return {
        "clusters": int(len(np.unique(etiquetas))),
        "peso_min": float(pd.Series(etiquetas).value_counts(normalize=True).min()),
        "silueta": (silhouette_score(Z, etiquetas, sample_size=min(3000, len(Z)),
                                     random_state=random_state) if varios else np.nan),
        "calinski_harabasz": calinski_harabasz_score(Z, etiquetas) if varios else np.nan,
        "davies_bouldin": davies_bouldin_score(Z, etiquetas) if varios else np.nan,
        f"ARI {nombre_y}": adjusted_rand_score(y, etiquetas),
        f"ARI {nombre_grupo}": adjusted_rand_score(grupos, etiquetas),
        f"NMI {nombre_y}": normalized_mutual_info_score(y, etiquetas),
        f"NMI {nombre_grupo}": normalized_mutual_info_score(grupos, etiquetas),
    }
