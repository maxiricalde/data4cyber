"""Interpretación y evaluación de clusters no supervisados.

El perfil de un cluster se lee con el z-score de su centroide: cuánto se aparta
la media del cluster de la media global, en unidades de desvío global. Un |z|
alto marca la variable que define el grupo porque se aleja de la media.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score,
                             davies_bouldin_score, normalized_mutual_info_score,
                             silhouette_score)


def zscore_columnas(valores):
    """Estandariza cada columna: media 0 y desvío 1, ignorando NaN.

    Equivale a ``scipy.stats.zscore(valores, axis=0, nan_policy="omit")``, con
    una diferencia: una columna constante queda en 0 en vez de dividir por cero.
    """
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
    """Perfil z-score de cada cluster: las variables que más lo definen.

    ``valores`` va en unidades originales (no escaladas) y ``etiquetas`` son
    las del clustering. Se omiten el ruido de DBSCAN (-1) y los clusters con
    menos de ``min_peso`` de las filas: un grupo residual no describe un régimen.
    """
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
    """Métricas de un clustering: internas, externas y tamaño.

    Internas: silueta, Calinski-Harabasz y Davies-Bouldin. Externas: ARI y NMI
    contra ``y`` y ``grupos``. Las externas son un control: si son altas, el
    clustering sigue esas etiquetas (ataque, escenario) en vez de describir
    estructura.
    """
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
