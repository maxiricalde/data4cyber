"""Despliegue supervisado y no supervisado.

Supervisado: ``GroupedPCA + XGBoost``. No supervisado: ``Birch`` sobre
invariantes físicos (ΔSOC, S_error, imbalance y balance nodal).

Uso::

    from src2.deploy import (entrenar_xgboost, exportar_portable, predecir,
                             entrenar_no_supervisado, exportar_no_supervisado,
                             predecir_no_supervisado)

    entrenar_xgboost()
    exportar_portable()
    pred = predecir("datasets/datasetS1alt.csv")

    entrenar_no_supervisado()
    exportar_no_supervisado()
    pred_ns = predecir_no_supervisado("datasets/datasetS1alt.csv")
"""

from __future__ import annotations

from pathlib import Path

import pickle

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import pairwise_distances_argmin_min
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import RobustScaler
from xgboost import XGBClassifier

from .data import eliminar_columnas, imputar_media
from .features import rango_movil, rango_por_escenario
from .group import GroupedPCA
from .train import PARAMS_XGB, SEED
from .unsupervised import Detector, entrenar_fold, prototipos

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
MEDIDORES = ["BSS-Inverter-AC-Meter", "Load-A-AC-Meter", "Load-B-AC-Meter",
             "PV-Inverter-AC-Meter", "Substation-AC-Meter"]
RAMAS = [m for m in MEDIDORES if m != "Substation-AC-Meter"]


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


# --------------------------------------------------------- no supervisado ----


def invariantes_fisicas(df: pd.DataFrame) -> pd.DataFrame:
    """Invariantes intra-medidor (ΔSOC, S_error, imbalance) + balance nodal (P, Q)."""
    inv = pd.DataFrame(index=df.index)
    inv["dsoc"] = (df["Battery-SOC-Reported.soc_value"]
                   - df["Battery-SOC-Reference.soc_value"]).abs()
    for medidor in MEDIDORES:
        p = df[f"{medidor}.p_sum3"]
        q = df[f"{medidor}.q_sum3"]
        s = df[f"{medidor}.s_sum3"]
        inv[f"{medidor}__serror"] = np.sqrt(p**2 + q**2) - s
        fases = [df[f"{medidor}.uln1"], df[f"{medidor}.uln2"], df[f"{medidor}.uln3"]]
        pares = [(fases[i] - fases[j]).abs() for i in range(3) for j in range(i + 1, 3)]
        inv[f"{medidor}__imbalance"] = pd.concat(pares, axis=1).max(axis=1)
    inv["balance_p"] = (df["Substation-AC-Meter.p_sum3"]
                        - sum(df[f"{m}.p_sum3"] for m in RAMAS))
    inv["balance_q"] = (df["Substation-AC-Meter.q_sum3"]
                        - sum(df[f"{m}.q_sum3"] for m in RAMAS))
    return inv


def _invariantes_por_escenario() -> tuple[dict, dict]:
    df = eliminar_columnas(_cargar())
    X_inv, Y = {}, {}
    for escenario, bloque in df.groupby("escenario", sort=False):
        X_inv[escenario] = invariantes_fisicas(
            bloque.drop(columns=["escenario", "attack_active"])
        ).reset_index(drop=True)
        Y[escenario] = bloque["attack_active"].reset_index(drop=True)
    return X_inv, Y


def entrenar_no_supervisado(salida: str = "modelos") -> dict:
    """Entrena y guarda el Birch no supervisado sobre invariantes físicos.

    Usa el mismo protocolo que ``loso``: entrena con todos los escenarios
    salvo ``ESCENARIO_TEST`` y calibra el umbral con el último 20 % benigno de
    cada escenario de entrenamiento.
    """
    X_inv, Y = _invariantes_por_escenario()
    X_fit, X_val = entrenar_fold(X_inv, Y, ESCENARIO_TEST)
    detector = Detector("birch").fit(X_fit, X_val)
    protos = prototipos(detector.modelo_, detector.Z_)

    carpeta = _raiz() / salida
    carpeta.mkdir(exist_ok=True)
    joblib.dump({
        "columnas_invariantes": list(X_fit.columns),
        "pipeline": detector.pipeline_,
        "birch_model": detector.modelo_,
        "birch_prototipos": protos,
        "birch_umbral": float(detector.umbral_),
        "escenario_test": ESCENARIO_TEST,
    }, carpeta / "birch_invariantes.joblib")

    print("escenarios de entrenamiento:",
          sorted(k for k in X_inv if k != ESCENARIO_TEST))
    print("X_fit:", X_fit.shape, "| X_val:", X_val.shape)
    print("prototipos Birch:", len(protos))
    print("umbral Birch (p95 benigno):", round(float(detector.umbral_), 4))
    print("guardado en:", carpeta)
    return {"detector": detector, "prototipos": protos}


def exportar_no_supervisado(salida: str = "deploy_nosupervisado.pkl",
                            carpeta: str = "modelos") -> dict:
    """Empaqueta Birch + invariantes en un único ``.pkl`` portable."""
    carpeta = _raiz() / carpeta
    modelo = joblib.load(carpeta / "birch_invariantes.joblib")

    paquete = {
        "kind": "unsupervised",
        "model_name": "birch_invariantes",
        "columnas_invariantes": modelo["columnas_invariantes"],
        "pipeline": modelo["pipeline"],
        "birch_model": modelo["birch_model"],
        "birch_prototipos": modelo["birch_prototipos"],
        "birch_umbral": modelo["birch_umbral"],
        "escenario_test": modelo.get("escenario_test"),
    }
    ruta = _raiz() / salida
    with open(ruta, "wb") as f:
        pickle.dump(paquete, f)
    print("paquete portable:", ruta)
    return paquete


def predecir_no_supervisado(csv_path, carpeta: str = "modelos") -> pd.DataFrame:
    """Score no supervisado sobre un CSV crudo con el modelo de ``entrenar_no_supervisado``.

    Devuelve un DataFrame con una fila por segundo: la distancia al prototipo
    benigno más cercano y la marca binaria según el umbral calibrado.
    """
    carpeta = _raiz() / carpeta
    modelo = joblib.load(carpeta / "birch_invariantes.joblib")

    df = pd.read_csv(csv_path)
    X_inv = invariantes_fisicas(df)[modelo["columnas_invariantes"]]
    Z = modelo["pipeline"].transform(X_inv)
    _, score = pairwise_distances_argmin_min(Z, modelo["birch_prototipos"])

    return pd.DataFrame({
        "score_birch": score,
        "flag_birch": (score > modelo["birch_umbral"]).astype(int),
    })


# ------------------------------------------------------------- regímenes ----


def _etiquetas_regimen(X: pd.DataFrame, etiquetas: np.ndarray) -> dict[int, str]:
    """Traduce cada cluster de KMeans a una etiqueta física legible."""
    perfil = X.assign(_cluster=etiquetas).groupby("_cluster").mean()
    cargas = (perfil["Load-A-AC-Meter__serror"]
              + perfil["Load-B-AC-Meter__serror"]) / 2
    pv = perfil["PV-Inverter-AC-Meter__serror"]

    magnitud = pd.concat([cargas.abs(), pv.abs()], axis=1).max(axis=1)
    neutral = int(magnitud.idxmin())
    resto = [int(c) for c in perfil.index if int(c) != neutral]
    cargas_id = max(resto, key=lambda c: cargas[c] - pv[c])
    pv_id = next(c for c in resto if c != cargas_id)

    return {
        neutral: "sin_inconsistencia_S",
        cargas_id: "inconsistencia_S_cargas",
        pv_id: "inconsistencia_S_PV",
    }


def entrenar_regimenes(salida: str = "modelos", k: int = 3) -> dict:
    if k != 3:
        raise ValueError("el etiquetador de regímenes está definido para k=3")

    X_inv, _ = _invariantes_por_escenario()
    X_all = pd.concat([X_inv[e] for e in X_inv], ignore_index=True)

    pipeline = make_pipeline(
        SimpleImputer(strategy="median"),
        RobustScaler(),
        PCA(n_components=0.95, random_state=SEED),
    )
    Z = pipeline.fit_transform(X_all)
    kmeans = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(Z)
    etiquetas = _etiquetas_regimen(X_all, kmeans.labels_)

    carpeta = _raiz() / salida
    carpeta.mkdir(exist_ok=True)
    joblib.dump({
        "columnas_invariantes": list(X_all.columns),
        "pipeline": pipeline,
        "kmeans_model": kmeans,
        "kmeans_centroides": kmeans.cluster_centers_,
        "k": k,
        "etiquetas": etiquetas,
        "escenarios": list(X_inv),
    }, carpeta / "regimenes_kmeans.joblib")

    print("escenarios:", list(X_inv))
    print("X_inv:", X_all.shape, "| componentes PCA:", Z.shape[1])
    print("etiquetas:", etiquetas)
    print("guardado en:", carpeta)
    return {"pipeline": pipeline, "kmeans": kmeans, "etiquetas": etiquetas}


def exportar_regimenes(salida: str = "deploy_regimenes.pkl",
                       carpeta: str = "modelos") -> dict:
    """Empaqueta el KMeans de regímenes en un único ``.pkl`` portable."""
    carpeta = _raiz() / carpeta
    modelo = joblib.load(carpeta / "regimenes_kmeans.joblib")

    paquete = {
        "kind": "regimenes",
        "model_name": "kmeans_invariantes",
        "columnas_invariantes": modelo["columnas_invariantes"],
        "pipeline": modelo["pipeline"],
        "kmeans_centroides": modelo["kmeans_centroides"],
        "k": modelo["k"],
        "etiquetas": modelo["etiquetas"],
    }
    ruta = _raiz() / salida
    with open(ruta, "wb") as f:
        pickle.dump(paquete, f)
    print("paquete portable:", ruta)
    return paquete


def predecir_regimenes(csv_path, carpeta: str = "modelos") -> pd.DataFrame:
   
    carpeta = _raiz() / carpeta
    modelo = joblib.load(carpeta / "regimenes_kmeans.joblib")

    df = pd.read_csv(csv_path)
    X_inv = invariantes_fisicas(df)[modelo["columnas_invariantes"]]
    Z = modelo["pipeline"].transform(X_inv)
    indice, _ = pairwise_distances_argmin_min(Z, modelo["kmeans_centroides"])
    etiquetas = modelo["etiquetas"]
    return pd.DataFrame({"regimen": [etiquetas[int(i)] for i in indice]})
