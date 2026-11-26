from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GridSearchCV, LeaveOneGroupOut, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import RFE

from .group import GroupedPCA
from .train import SEED, _metricas


def buscar_grid_rfe(X, y, grupos, clasificador, n_features,
                    step=5, espacio_modelo=None,
                    scoring="accuracy", cv=None, n_jobs=-1, verbose=1):
    """GridSearchCV con RFE y LOSO."""
    espacio = {"rfe__n_features_to_select": n_features}
    if espacio_modelo:
        espacio.update(espacio_modelo)

    pipeline = Pipeline([
        ("rfe", RFE(estimator=clasificador, step=step)),
        ("modelo", clasificador),
    ])

    busqueda = GridSearchCV(
        pipeline,
        espacio,
        cv=LeaveOneGroupOut() if cv is None else cv,
        scoring=scoring,
        n_jobs=n_jobs,
        verbose=verbose,
        return_train_score=True,
    )
    busqueda.fit(X, y, groups=grupos)
    return busqueda


def buscar_random(X, y, grupos, clasificador, espacio, n_iter=30,
                  scoring="accuracy", cv=None, n_jobs=-1, verbose=1,
                  random_state=SEED):
    """RandomizedSearchCV con block PCA fijo y LOSO."""
    busqueda = RandomizedSearchCV(
        pipeline_block(clasificador),
        espacio,
        n_iter=n_iter,
        scoring=scoring,
        cv=cv_loso() if cv is None else cv,
        n_jobs=n_jobs,
        verbose=verbose,
        random_state=random_state,
        return_train_score=True,
    )
    busqueda.fit(X, y, groups=grupos)
    return busqueda


def buscar_grid(X, y, grupos, clasificador, espacio, scoring="accuracy",
                cv=None, n_jobs=-1, verbose=1):
    """GridSearchCV con block PCA fijo y LOSO.

    espacio usa el prefijo modelo__... porque los parámetros de GroupedPCA
    quedan fijos. Ejemplo: {"modelo__n_estimators": [100, 200]}.
    """
    busqueda = GridSearchCV(
        pipeline_block(clasificador),
        espacio,
        cv=cv_loso() if cv is None else cv,
        scoring=scoring,
        n_jobs=n_jobs,
        verbose=verbose,
        return_train_score=True,
    )
    busqueda.fit(X, y, groups=grupos)
    return busqueda


def pipeline_block(clasificador, varianza=0.95, umbral=0.3):
    """Arma GroupedPCA con parámetros fijos y el clasificador."""
    return Pipeline([
        ("block", GroupedPCA(n_components=varianza, t=umbral, random_state=SEED)),
        ("modelo", clasificador),
    ])


def cv_loso():
    """CV que deja un escenario afuera por fold."""
    return LeaveOneGroupOut()


def tabla_resultados(busqueda):
    """Filas de cv_results_ ordenadas por rank, con las columnas útiles."""
    tabla = pd.DataFrame(busqueda.cv_results_)
    columnas = [c for c in tabla.columns if c.startswith("param_")]
    columnas += ["mean_test_score", "std_test_score", "rank_test_score"]
    return tabla[columnas].sort_values("rank_test_score")


def rf_pipeline_logo(pipeline, X, y, grupos):
    """LOSO de un pipeline completo (reductor + clasificador)."""
    y = np.asarray(y).ravel()
    grupos = np.asarray(grupos)
    filas = []
    for fold, (tr, te) in enumerate(
            LeaveOneGroupOut().split(X, y, groups=grupos), start=1):
        modelo = clone(pipeline).fit(X.iloc[tr], y[tr])
        proba = modelo.predict_proba(X.iloc[te])[:, 1]
        fila = {
            "fold": fold,
            "escenario": grupos[te][0],
            "features": int(modelo.named_steps["modelo"].n_features_in_),
        }
        fila["accuracy_train"] = modelo.score(X.iloc[tr], y[tr])
        fila.update(_metricas(y[te], proba))
        filas.append(fila)
    tabla = pd.DataFrame(filas).set_index("fold").round(3)
    tabla.loc["mean"] = tabla.mean(numeric_only=True).round(3)
    return tabla


def elegir_por_gap(busqueda, tolerancia=0.02):
    """Entre los candidatos cerca del mejor test, elige el de menor gap."""
    tabla = pd.DataFrame(busqueda.cv_results_)
    tabla["gap"] = tabla["mean_train_score"] - tabla["mean_test_score"]

    umbral = tabla["mean_test_score"].max() - tolerancia
    candidatos = tabla[tabla["mean_test_score"] >= umbral]
    elegido = candidatos.sort_values("gap").iloc[0]

    params = {
        columna.replace("param_", ""): elegido[columna]
        for columna in tabla.columns
        if columna.startswith("param_")
    }

    return {
        "params": params,
        "score": float(elegido["mean_test_score"]),
        "gap": float(elegido["gap"]),
        "pipeline": clone(busqueda.estimator).set_params(**params),
    }


def resumen_pipeline(nombre, tabla):
    """Una fila con las métricas que venís usando en SUPERVISADO."""
    d = tabla.drop(index="mean", errors="ignore")
    ataque = d[d["escenario"] != "S0"]

    return {
        "configuración": nombre,
        "features": int(d["features"].iloc[0]),
        "accuracy train": d["accuracy_train"].mean(),
        "accuracy test": d["accuracy"].mean(),
        "gap": d["accuracy_train"].mean() - d["accuracy"].mean(),
        "F1": ataque["f1"].mean(),
        "recall@5": ataque["recall_5"].mean(),
        "recall": ataque["recall"].mean(),
        "espec S0": float(d.loc[d["escenario"] == "S0", "especificidad"].iloc[0]),
    }


def evaluar_pipeline(pipeline, X, y, grupos, nombre):
    """Evalúa un pipeline con LOSO y devuelve tabla por fold + fila resumen."""
    tabla = rf_pipeline_logo(pipeline, X, y, grupos)
    fila = pd.DataFrame([resumen_pipeline(nombre, tabla)]).set_index("configuración")
    return tabla, fila


def tunear_clasificador(X, y, grupos, clasificador, espacio, nombre,
                        modo="random", n_iter=30, tolerancia=0.02,
                        scoring="accuracy", n_jobs=-1, verbose=1,
                        random_state=SEED):
    """RandomizedSearch o GridSearch + selección por gap + evaluación LOSO."""
    if modo == "random":
        busqueda = buscar_random(
            X, y, grupos, clasificador, espacio,
            n_iter=n_iter, scoring=scoring, n_jobs=n_jobs,
            verbose=verbose, random_state=random_state,
        )
    elif modo == "grid":
        busqueda = buscar_grid(
            X, y, grupos, clasificador, espacio,
            scoring=scoring, n_jobs=n_jobs, verbose=verbose,
        )
    else:
        raise ValueError("modo debe ser 'random' o 'grid'")

    elegido = elegir_por_gap(busqueda, tolerancia)
    tabla, fila = evaluar_pipeline(elegido["pipeline"], X, y, grupos, nombre)
    return {
        "busqueda": busqueda,
        "elegido": elegido,
        "tabla": tabla,
        "fila": fila,
    }
