"""Despliegue: entrena y guarda los modelos finales y predice sobre CSV crudo.

Supervisado: ``GroupedPCA + XGBoost`` con los mejores hiperparámetros del grid
local, entrenado sobre todos los escenarios salvo ``S1-alt``, que queda
reservado para probar el modelo.

No supervisado: ``Detector("birch")`` (distancia al prototipo benigno más
cercano + umbral p95), entrenado solo con las filas benignas de esos escenarios.

Uso::

    from src2.deploy import entrenar, predecir

    entrenar()
    pred = predecir("datasets/datasetS1alt.csv")
"""

from __future__ import annotations

from pathlib import Path

import pickle

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from .data import eliminar_columnas, imputar_media
from .features import rango_movil, rango_por_escenario
from .group import GroupedPCA
from .train import PARAMS_XGB, SEED
from .unsupervised import Detector

BEST_XGB = {
    "learning_rate": 0.01,
    "max_depth": 2,
    "n_estimators": 50,
    "subsample": 0.5,
}
ESCENARIO_TEST = "S1-alt"
ARCHIVOS = {
    "S0": "datasetS0.csv",
    "S1": "datasetS1.csv",
    "S1-alt": "datasetS1alt.csv",
    "S2": "datasetS2.csv",
    "S3": "datasetS3.csv",
    "S4": "datasetS4.csv",
    "S5": "datasetS5.csv",
    "S6": "datasetS6.csv",
}


def _raiz() -> Path:
    """Raíz del repo: la carpeta que contiene ``datasets/``."""
    ruta = Path.cwd()
    if not (ruta / "datasets").exists():
        ruta = ruta.parent
    return ruta


def _cargar() -> pd.DataFrame:
    base = _raiz() / "datasets"
    dfs = {k: pd.read_csv(base / f) for k, f in ARCHIVOS.items()}
    return (pd.concat(dfs, names=["escenario"])
            .reset_index(level="escenario")
            .reset_index(drop=True))


def _pipeline_xgb() -> Pipeline:
    params = {**PARAMS_XGB, "n_jobs": 1, **BEST_XGB}
    return Pipeline([
        ("block", GroupedPCA(n_components=0.95, t=0.3, random_state=SEED)),
        ("modelo", XGBClassifier(**params)),
    ])


def entrenar(salida: str = "modelos") -> dict:
    """Entrena y guarda el XGB supervisado y el detector Birch.

    Entrena con todos los escenarios salvo ``ESCENARIO_TEST``. Guarda en
    ``salida/``: ``xgb_blockpca.joblib``, ``birch.joblib`` y ``preproceso.joblib``
    (columnas y medias de imputación).
    """
    df = _cargar()
    df = eliminar_columnas(df)

    medias = df.drop(columns=["escenario", "attack_active"]).mean()
    df = imputar_media(df)

    train = df[df["escenario"] != ESCENARIO_TEST]
    X_rango = rango_por_escenario(train.drop(columns=["attack_active"]))
    y = train["attack_active"].to_numpy()

    xgb = _pipeline_xgb().fit(X_rango, y)
    detector = Detector("birch").fit(X_rango[y == 0])

    carpeta = _raiz() / salida
    carpeta.mkdir(exist_ok=True)
    joblib.dump(xgb, carpeta / "xgb_blockpca.joblib")
    joblib.dump(detector, carpeta / "birch.joblib")
    joblib.dump(
        {"columnas": list(X_rango.columns), "medias": medias.to_dict()},
        carpeta / "preproceso.joblib",
    )

    print("escenarios de entrenamiento:", sorted(train["escenario"].unique()))
    print("X_rango:", X_rango.shape, "| positivos:", int(y.sum()))
    print("umbral Birch (p95 benigno):", round(float(detector.umbral_), 4))
    print("guardado en:", carpeta)
    return {"xgb": xgb, "birch": detector}


def exportar_portable(salida: str = "modelo_deploy.pkl",
                      carpeta: str = "modelos") -> dict:
    """Empaqueta todo en un único ``.pkl`` con solo objetos de sklearn/numpy.

    No guarda las clases de ``src2`` (``GroupedPCA``, ``Detector``): guarda los
    bloques ya ajustados y los modelos crudos, para que ``deploy_portable.py``
    pueda predecir sin importar el proyecto.
    """
    carpeta = _raiz() / carpeta
    xgb = joblib.load(carpeta / "xgb_blockpca.joblib")
    detector = joblib.load(carpeta / "birch.joblib")
    preproceso = joblib.load(carpeta / "preproceso.joblib")

    paquete = {
        "columnas": preproceso["columnas"],
        "medias": preproceso["medias"],
        "ventana": 120,
        "xgb_model": xgb.named_steps["modelo"],
        "pca_blocks": xgb.named_steps["block"].blocks_,
        "birch_pipe": detector.pipeline_,
        "birch_model": detector.modelo_,
        "birch_Z": detector.Z_,
        "birch_umbral": float(detector.umbral_),
    }
    ruta = _raiz() / salida
    with open(ruta, "wb") as f:
        pickle.dump(paquete, f)
    print("paquete portable:", ruta)
    return paquete


def _preprocesar(df: pd.DataFrame, preproceso: dict) -> pd.DataFrame:
    df = eliminar_columnas(df)
    if "attack_active" in df.columns:
        df = df.drop(columns="attack_active")
    for col, media in preproceso["medias"].items():
        if col in df.columns:
            df[col] = df[col].fillna(media)
    return rango_movil(df, 120)[preproceso["columnas"]]


def predecir(csv_path, carpeta: str = "modelos") -> pd.DataFrame:
    """Score sobre un CSV crudo con los modelos guardados por ``entrenar``.

    Devuelve un DataFrame con una fila por segundo: la probabilidad de ataque
    del XGB y el score/flag del detector Birch.
    """
    carpeta = _raiz() / carpeta
    xgb = joblib.load(carpeta / "xgb_blockpca.joblib")
    detector = joblib.load(carpeta / "birch.joblib")
    preproceso = joblib.load(carpeta / "preproceso.joblib")

    X_rango = _preprocesar(pd.read_csv(csv_path), preproceso)

    proba = xgb.predict_proba(X_rango)[:, 1]
    score = detector.score(X_rango)
    return pd.DataFrame({
        "prob_ataque_xgb": proba,
        "score_birch": score,
        "flag_birch": (score > detector.umbral_).astype(int),
    })
