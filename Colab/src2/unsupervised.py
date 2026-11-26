

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import Birch, DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import (confusion_matrix, pairwise_distances_argmin_min,
                             roc_auc_score, silhouette_score)
from sklearn.model_selection import KFold, cross_val_score
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .train import recall_5

SEED = 42
MODELOS = ("kmeans", "birch", "dbscan")


def escala_vecinos(Z, k=5, percentil=90):
    """Distancia típica al k-ésimo vecino: escala para Birch y DBSCAN."""
    vecinos = NearestNeighbors(n_neighbors=k + 1).fit(Z)
    distancias, _ = vecinos.kneighbors(Z)
    return max(float(np.percentile(distancias[:, -1], percentil)), 1e-6)


def elegir_k(Z, rango=range(2, 11), muestra=2000):
    mejor_k, mejor_silueta = None, -1.0
    for k in rango:
        etiquetas = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(Z)
        silueta = silhouette_score(
            Z, etiquetas, sample_size=min(muestra, len(Z)), random_state=SEED
        )
        if silueta > mejor_silueta:
            mejor_k, mejor_silueta = k, silueta
    return mejor_k


def crear_modelo(nombre, Z):
    if nombre == "kmeans":
        return KMeans(n_clusters=elegir_k(Z), n_init=10, random_state=SEED)

    escala = escala_vecinos(Z)
    if nombre == "birch":
        return Birch(threshold=escala, n_clusters=None)
    if nombre == "dbscan":
        return DBSCAN(eps=escala, min_samples=5)
    raise ValueError(f"modelo desconocido: {nombre!r}")


def prototipos(modelo, respaldo=None):
    for atributo in ("cluster_centers_", "subcluster_centers_", "components_"):
        if hasattr(modelo, atributo):
            puntos = getattr(modelo, atributo)
            if len(puntos) > 0:
                return puntos
    if respaldo is not None:
        return respaldo
    raise ValueError("el modelo no expone prototipos")


def distancia_al_prototipo(modelo, Z, respaldo=None):
    _, distancias = pairwise_distances_argmin_min(Z, prototipos(modelo, respaldo))
    return distancias


def metricas(y, score, umbral):
    y = np.asarray(y, dtype=int)
    pred = (score > umbral).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    dos_clases = len(np.unique(y)) > 1
    return {
        "n": len(y),
        "positivos": int(y.sum()),
        "auc": roc_auc_score(y, score) if dos_clases else np.nan,
        "recall_5": recall_5(y, score) if dos_clases else np.nan,
        "recall": tp / (tp + fn) if (tp + fn) else np.nan,
        "especificidad": tn / (tn + fp) if (tn + fp) else np.nan,
        "umbral": float(umbral),
        "flagged": int(pred.sum()),
    }


class Detector:
    def __init__(self, modelo="kmeans", varianza=0.95, q=95):
        self.modelo = modelo
        self.varianza = varianza
        self.q = q

    def fit(self, X_benigno, X_validacion=None):
        """Ajusta preproceso y prototipos; calibra el umbral con benigno."""
        pasos = [SimpleImputer(strategy="median"), StandardScaler()]
        if self.varianza is not None:
            pasos.append(PCA(n_components=self.varianza, random_state=SEED))
        self.pipeline_ = make_pipeline(*pasos).fit(X_benigno)

        Z = self.pipeline_.transform(X_benigno)
        self.modelo_ = crear_modelo(self.modelo, Z).fit(Z)
        self.Z_ = Z

        calibracion = X_benigno if X_validacion is None else X_validacion
        self.umbral_ = self.umbral(self.score(calibracion))
        return self

    def score(self, X):
        """Distancia de cada fila al prototipo benigno más cercano."""
        Z = self.pipeline_.transform(X)
        return distancia_al_prototipo(self.modelo_, Z, respaldo=self.Z_)

    def umbral(self, scores):
        """Percentil ``q`` de unos scores dados; calibra el umbral."""
        return float(np.percentile(scores, self.q))


def _mascara_validacion(grupo, y, fraccion=0.2):
    """Último tramo cronológico del benigno de cada escenario de entrenamiento."""
    mascara = np.zeros(len(y), dtype=bool)
    for nombre in pd.unique(grupo):
        filas = np.where((grupo == nombre) & (y == 0))[0]
        if len(filas) == 0:
            continue
        corte = int(len(filas) * (1 - fraccion))
        mascara[filas[corte:]] = True
    return mascara


def entrenar_fold(dfsX, dfsY, test):
    partes_X, partes_y, partes_grupo = [], [], []
    for nombre in dfsX:
        if nombre == test:
            continue
        partes_X.append(dfsX[nombre])
        partes_y.append(dfsY[nombre])
        partes_grupo.append(np.full(len(dfsX[nombre]), nombre))

    X_train = pd.concat(partes_X, ignore_index=True)
    y_train = np.concatenate(partes_y)
    grupo = np.concatenate(partes_grupo)
    mascara_benigna = y_train == 0
    validacion = _mascara_validacion(grupo, y_train)

    X_fit = X_train.loc[mascara_benigna & ~validacion]
    X_val = X_train.loc[validacion]
    if len(X_val) == 0:
        X_fit, X_val = X_train.loc[mascara_benigna], X_train.loc[mascara_benigna]
    assert (y_train[mascara_benigna & ~validacion] == 0).all()
    return X_fit, X_val


def loso(dfsX, dfsY, modelo="kmeans", varianza=0.95):
    filas = []
    for test in dfsX:
        X_fit, X_val = entrenar_fold(dfsX, dfsY, test)
        detector = Detector(modelo, varianza=varianza).fit(X_fit, X_val)

        X_test = dfsX[test].reset_index(drop=True)
        y_test = np.asarray(dfsY[test])
        fila = {"escenario": test, "modelo": modelo}
        fila.update(metricas(y_test, detector.score(X_test), detector.umbral_))
        filas.append(fila)
    return pd.DataFrame(filas)


def control_posicion(X, y, grupo):
    """AUC de la posición sola y R² de predecir la posición desde las features."""
    y = np.asarray(y)
    filas = []
    for nombre in pd.unique(grupo):
        mascara = grupo == nombre
        X_escenario = X.loc[mascara].reset_index(drop=True)
        y_escenario = y[mascara]
        posicion = np.linspace(0.0, 1.0, len(X_escenario))

        auc = (roc_auc_score(y_escenario, posicion)
               if len(np.unique(y_escenario)) > 1 else np.nan)
        prediccion = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            Ridge(),
        )
        # Interpolar mide cuánto tiempo codifican las features; con bloques
        # contiguos, el modelo además tiene que extrapolar y eso no es lo que
        # queremos medir acá.
        r2_interpolacion = cross_val_score(
            prediccion, X_escenario, posicion,
            cv=KFold(5, shuffle=True, random_state=SEED), scoring="r2",
        ).mean()
        r2_extrapolacion = cross_val_score(
            prediccion, X_escenario, posicion, cv=KFold(5), scoring="r2",
        ).mean()

        filas.append({
            "escenario": nombre,
            "auc_posicion": auc,
            "r2_posicion": r2_interpolacion,
            "r2_extrapolacion": r2_extrapolacion,
        })
    return pd.DataFrame(filas)


def residualizar_tiempo(X, pos, grupo):
    """Saca de cada columna la tendencia lineal con la posición, por escenario."""
    grupo = np.asarray(grupo)
    pos = np.asarray(pos)
    salida = pd.DataFrame(index=X.index, columns=X.columns, dtype=float)

    for nombre in pd.unique(grupo):
        filas = np.where(grupo == nombre)[0]
        bloque = SimpleImputer(strategy="median").fit_transform(X.iloc[filas])
        posicion = pos[filas].reshape(-1, 1)
        prediccion = LinearRegression().fit(posicion, bloque).predict(posicion)
        salida.iloc[filas] = bloque - prediccion
    return salida
