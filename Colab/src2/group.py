import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted


class GroupedPCA(BaseEstimator, TransformerMixin):
    """Agrupa variables por |r| (average linkage) y aplica PCA por bloque."""

    def __init__(self, n_components=0.95, t=0.3, method="average", random_state=0):
        self.n_components = n_components
        self.t = t
        self.method = method
        self.random_state = random_state

    def fit(self, X, y=None):
        X = pd.DataFrame(X)
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)

        R = X.corr().abs().fillna(0)
        D = (1 - R).to_numpy().copy()
        np.fill_diagonal(D, 0)
        Z = linkage(squareform(D, checks=False), method=self.method)
        etiquetas = fcluster(Z, t=self.t, criterion="distance")

        bloques = pd.Series(etiquetas, index=X.columns)
        self.grupos_ = [g.index.tolist() for _, g in bloques.groupby(bloques)]

        self.blocks_ = []
        for cols in self.grupos_:
            escalador, pca = None, None
            if len(cols) > 1:
                valores = X[cols].to_numpy()
                escalador = StandardScaler().fit(valores)
                pca = PCA(n_components=self.n_components,
                          random_state=self.random_state).fit(
                              escalador.transform(valores))
            self.blocks_.append((cols, escalador, pca))
        return self

    def transform(self, X):
        check_is_fitted(self, "blocks_")
        Xd = X if isinstance(X, pd.DataFrame) else \
             pd.DataFrame(X, columns=self.feature_names_in_)
        partes = []
        for cols, escalador, pca in self.blocks_:
            parte = Xd[cols].to_numpy()
            if pca is not None:
                parte = pca.transform(escalador.transform(parte))
            partes.append(parte)
        return np.hstack(partes)

    def get_feature_names_out(self, input_features=None):
        nombres = []
        for i, (cols, _, pca) in enumerate(self.blocks_):
            if pca is None:
                nombres.append(f"g{i}_{cols[0]}")
            else:
                nombres += [f"g{i}_pc{j+1}" for j in range(pca.n_components_)]
        return np.asarray(nombres, dtype=object)