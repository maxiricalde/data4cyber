"""Reductores de columnas que se ajustan dentro de cada fold."""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class CorrFilter(BaseEstimator, TransformerMixin):
    """Descarta una columna de cada par con |r| mayor que `umbral`."""

    def __init__(self, umbral=0.95):
        self.umbral = umbral

    def fit(self, X, y=None):
        correlacion = X.corr().abs()
        arriba = correlacion.where(np.triu(np.ones(correlacion.shape, dtype=bool), k=1))
        self.columnas_ = [c for c in X.columns if not (arriba[c] > self.umbral).any()]
        return self

    def transform(self, X):
        return X[self.columnas_]
