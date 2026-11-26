"""Despliegue supervisado: entrena ``GroupedPCA + XGBoost`` y exporta el ``.pkl``.

Entrena con los mejores hiperparámetros del grid local sobre todos los
escenarios salvo ``S1-alt``, que queda reservado para probar el modelo.

Uso::

    from src2.deploy import entrenar_xgboost, exportar_portable, predecir

    entrenar_xgboost()
    exportar_portable()
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

BEST_XGB = {
    "learning_rate": 0.01,
    "max_depth": 2,
    "n_estimators": 50,
    "subsample": 0.5,
}
UMBRAL_XGB = 0.5
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


def entrenar_xgboost(salida: str = "modelos") -> dict:
    """Entrena y guarda el XGB supervisado.

    Entrena con todos los escenarios salvo ``ESCENARIO_TEST``. Guarda en
    ``salida/``: ``xgb_blockpca.joblib`` y ``preproceso.joblib`` (columnas y
    medias de imputación).
    """
    df = _cargar()
    df = eliminar_columnas(df)

    medias = df.drop(columns=["escenario", "attack_active"]).mean()
    df = imputar_media(df)

    train = df[df["escenario"] != ESCENARIO_TEST]
    X_rango = rango_por_escenario(train.drop(columns=["attack_active"]))
    y = train["attack_active"].to_numpy()

    xgb = _pipeline_xgb().fit(X_rango, y)

    carpeta = _raiz() / salida
    carpeta.mkdir(exist_ok=True)
    joblib.dump(xgb, carpeta / "xgb_blockpca.joblib")
    joblib.dump(
        {"columnas": list(X_rango.columns), "medias": medias.to_dict()},
        carpeta / "preproceso.joblib",
    )

    print("escenarios de entrenamiento:", sorted(train["escenario"].unique()))
    print("X_rango:", X_rango.shape, "| positivos:", int(y.sum()))
    print("guardado en:", carpeta)
    return {"xgb": xgb}


def exportar_portable(salida: str = "modelo_deploy.pkl",
                      carpeta: str = "modelos") -> dict:
    """Empaqueta el XGB supervisado en un único ``.pkl`` portable.

    No guarda las clases de ``src2`` (``GroupedPCA``): guarda los bloques ya
    ajustados y el modelo crudo, para que ``deploy_supervisado.py`` pueda
    predecir sin importar el proyecto.
    """
    carpeta = _raiz() / carpeta
    xgb = joblib.load(carpeta / "xgb_blockpca.joblib")
    preproceso = joblib.load(carpeta / "preproceso.joblib")

    paquete = {
        "kind": "supervised",
        "model_name": "xgb_blockpca",
        "columnas": preproceso["columnas"],
        "medias": preproceso["medias"],
        "ventana": 120,
        "xgb_model": xgb.named_steps["modelo"],
        "pca_blocks": xgb.named_steps["block"].blocks_,
        "xgb_umbral": UMBRAL_XGB,
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


def predecir(csv_path, carpeta: str = "modelos",
             umbral: float = UMBRAL_XGB) -> pd.DataFrame:
    """Score supervisado sobre un CSV crudo con los modelos de ``entrenar_xgboost``.

    Devuelve un DataFrame con una fila por segundo: la probabilidad de ataque
    del XGB y la marca binaria según ``umbral``.
    """
    carpeta = _raiz() / carpeta
    xgb = joblib.load(carpeta / "xgb_blockpca.joblib")
    preproceso = joblib.load(carpeta / "preproceso.joblib")

    X_rango = _preprocesar(pd.read_csv(csv_path), preproceso)

    proba = xgb.predict_proba(X_rango)[:, 1]
    return pd.DataFrame({
        "prob_ataque_xgb": proba,
        "ataque_xgb": (proba >= umbral).astype(int),
    })
