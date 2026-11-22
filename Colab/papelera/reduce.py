"""Reductores de columnas: se ajustan con el train y se aplican a cualquier frame."""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.decomposition import PCA
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42


class CorrFilter:
    """Se queda con una columna de cada par con |r| mayor que `umbral`."""

    def __init__(self, umbral=0.95):
        self.umbral = umbral

    def fit(self, X):
        correlacion = X.corr().abs()
        arriba = correlacion.where(np.triu(np.ones(correlacion.shape, dtype=bool), k=1))
        self.columnas_ = [c for c in X.columns if not (arriba[c] > self.umbral).any()]
        return self

    def transform(self, X):
        return X[self.columnas_].to_numpy()


class PcaReduce:
    """Imputa, escala y proyecta con PCA."""

    def __init__(self, varianza=0.95):
        self.varianza = varianza

    def fit(self, X):
        self.pipeline_ = Pipeline([
            ("imputar", SimpleImputer(strategy="median")),
            ("escalar", StandardScaler()),
            ("pca", PCA(n_components=self.varianza, random_state=SEED)),
        ]).fit(X)
        return self

    def transform(self, X):
        return self.pipeline_.transform(X)


def _bloques(X_train, umbral):
    """Agrupa columnas que se mueven juntas: |r| >= umbral, average linkage."""
    correlacion = X_train.corr().abs().fillna(0.0).to_numpy()
    distancia = 1.0 - correlacion
    np.fill_diagonal(distancia, 0.0)
    arbol = linkage(squareform(distancia, checks=False), method="average")
    return pd.Series(fcluster(arbol, t=1.0 - umbral, criterion="distance"), index=X_train.columns)


class BlockPca:
    """Un PCA por bloque de columnas correlacionadas; los bloques de una pasan tal cual."""

    def __init__(self, varianza=0.95, umbral=0.70):
        self.varianza = varianza
        self.umbral = umbral

    def fit(self, X):
        self.columnas_ = list(X.columns)
        self.imputador_ = SimpleImputer(strategy="median").fit(X)
        limpio = pd.DataFrame(self.imputador_.transform(X), columns=self.columnas_)

        self.mantener_ = VarianceThreshold().fit(limpio).get_support()
        limpio = limpio.loc[:, self.mantener_]

        grupos = _bloques(limpio, self.umbral)
        self.bloques_ = []
        for _, columnas in grupos.groupby(grupos):
            nombres = list(columnas.index)
            escalador = StandardScaler().fit(limpio[nombres])
            if len(nombres) > 1:
                pca = PCA(n_components=self.varianza, random_state=SEED).fit(
                    escalador.transform(limpio[nombres])
                )
                self.bloques_.append((nombres, escalador, pca))
            else:
                self.bloques_.append((nombres, escalador, None))
        return self

    def transform(self, X):
        limpio = pd.DataFrame(self.imputador_.transform(X), columns=self.columnas_)
        limpio = limpio.loc[:, self.mantener_]
        partes = []
        for nombres, escalador, pca in self.bloques_:
            bloque = escalador.transform(limpio[nombres])
            partes.append(pca.transform(bloque) if pca is not None else bloque)
        return np.hstack(partes)


REDUCTORES = {"ninguna": None, "corr": CorrFilter, "pca": PcaReduce, "block_pca": BlockPca}
