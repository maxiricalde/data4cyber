"""Modelos y evaluación del supervisado: LOSO, CV, punto de operación y resumen."""

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score,
                             roc_curve)
from sklearn.model_selection import StratifiedKFold,LeaveOneGroupOut
from xgboost import XGBClassifier
from src2.group import GroupedPCA
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import RFE
SEED = 42

PARAMS_RF = {
    "n_estimators": 120,
    "max_depth": 18,
    "min_samples_leaf": 2,
    "class_weight": "balanced",
    "random_state": SEED,
    "n_jobs": -1,
}

PARAMS_XGB = {
    "n_estimators": 300,
    "max_depth": 4,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "tree_method": "hist",
    "eval_metric": "logloss",
    "random_state": SEED,
    "n_jobs": -1,
}


def recall_5(y_true, score, fpr=0.05):
    """TPR al 5 % de falsos positivos, leído de la curva ROC.

    No depende de un umbral fijo: mide qué fracción de los ataques entra en la
    banda de mayor score que el operador toleraría.
    """
    f, t, _ = roc_curve(y_true, score)
    return float(np.interp(fpr, f, t))


def _ajustar_reductor(reductor, X_train, X_test):
    """Ajusta el reductor con el train y transforma los dos frames."""
    if reductor is None:
        return X_train.to_numpy(), X_test.to_numpy()
    ajustado = reductor().fit(X_train)
    return ajustado.transform(X_train), ajustado.transform(X_test)


def _metricas(y_true, proba):
    """Las métricas de siempre, con umbral 0.5 y con recall@5."""
    pred = (proba >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "n": len(y_true),
        "positivos": int(y_true.sum()),
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "especificidad": tn / (tn + fp) if (tn + fp) else np.nan,
        "auc": roc_auc_score(y_true, proba) if len(np.unique(y_true)) > 1 else np.nan,
        "recall_5": recall_5(y_true, proba) if len(np.unique(y_true)) > 1 else np.nan,
    }


def _loso(dfsX, dfsY, modelo, reductor=None):
    """Un fold por escenario; el reductor se ajusta con el train de cada fold."""
    filas = []
    for test in dfsX:
        otros = [k for k in dfsX if k != test]
        X_train = pd.concat([dfsX[k] for k in otros], ignore_index=True)
        y_train = pd.concat([dfsY[k] for k in otros], ignore_index=True)
        X_test = dfsX[test].reset_index(drop=True)
        y_test = dfsY[test].to_numpy()

        X_train, X_test = _ajustar_reductor(reductor, X_train, X_test)
        rf = clone(modelo).fit(X_train, y_train)

        fila = {"escenario": test, "features": X_train.shape[1]}
        fila.update(_metricas(y_test, rf.predict_proba(X_test)[:, 1]))
        filas.append(fila)

    return pd.DataFrame(filas).set_index("escenario").round(3)


def rf_LOSO(dfsX, dfsY, reductor=None):
    """Random Forest, un escenario afuera."""
    return _loso(dfsX, dfsY, RandomForestClassifier(**PARAMS_RF), reductor)


def xgb_LOSO(dfsX, dfsY, reductor=None):
    """XGBoost, un escenario afuera."""
    return _loso(dfsX, dfsY, XGBClassifier(**PARAMS_XGB), reductor)

def especificidad_s0(dfsX, dfsY, X_s0, tpr=0.95, reductor=None):
    """Entrena con los escenarios de ataque y mide especificidad sobre S0.

    El umbral sale de los positivos del entrenamiento: primero se fija cuánto
    ataque se quiere detectar, después se cuenta cuánto benigno se marca de más.
    """
    X_train = pd.concat([dfsX[k] for k in dfsX], ignore_index=True)
    y_train = pd.concat([dfsY[k] for k in dfsX], ignore_index=True)

    X_train, X_s0 = _ajustar_reductor(reductor, X_train, X_s0.reset_index(drop=True))
    rf = RandomForestClassifier(**PARAMS_RF).fit(X_train, y_train)

    score_train = rf.predict_proba(X_train)[:, 1]
    umbral = np.quantile(score_train[y_train.to_numpy() == 1], 1 - tpr)
    return float(np.mean(rf.predict_proba(X_s0)[:, 1] < umbral))


def tabla_umbral(dfsX, dfsY, tpr=0.95, reductor=None):
    """Métricas por fold con el umbral que da `tpr` sobre el train de cada fold."""
    filas = []
    for test in dfsX:
        otros = [k for k in dfsX if k != test]
        X_train = pd.concat([dfsX[k] for k in otros], ignore_index=True)
        y_train = pd.concat([dfsY[k] for k in otros], ignore_index=True)
        X_test = dfsX[test].reset_index(drop=True)
        y_test = dfsY[test].to_numpy()

        X_train, X_test = _ajustar_reductor(reductor, X_train, X_test)
        rf = RandomForestClassifier(**PARAMS_RF).fit(X_train, y_train)

        score_train = rf.predict_proba(X_train)[:, 1]
        umbral = np.quantile(score_train[y_train.to_numpy() == 1], 1 - tpr)
        pred = (rf.predict_proba(X_test)[:, 1] >= umbral).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()

        filas.append({
            "escenario": test,
            "umbral": umbral,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "recall": tp / (tp + fn) if (tp + fn) else np.nan,
            "especificidad": tn / (tn + fp) if (tn + fp) else np.nan,
            "precision": tp / (tp + fp) if (tp + fp) else np.nan,
        })

    return pd.DataFrame(filas).set_index("escenario").round(3)


def loso_anidado(dfsX, dfsY, candidatos):
    """Elige el reductor dentro del train de cada fold y evalúa en el test.

    `candidatos` es un diccionario `{nombre: clase_del_reductor}`. La elección se
    hace reteniendo, uno por uno, los escenarios del propio train; el escenario
    de test nunca participa.
    """
    modelo = RandomForestClassifier(**PARAMS_RF)
    filas = []

    for test in dfsX:
        otros = [k for k in dfsX if k != test]

        # --- elección interna: se retiene un escenario del propio train ---
        puntajes = {}
        for nombre, reductor in candidatos.items():
            aucs = []
            for interno in otros:
                dentro = [k for k in otros if k != interno]
                X_tr = pd.concat([dfsX[k] for k in dentro], ignore_index=True)
                y_tr = pd.concat([dfsY[k] for k in dentro], ignore_index=True)
                X_va = dfsX[interno].reset_index(drop=True)
                y_va = dfsY[interno].to_numpy()

                X_tr, X_va = _ajustar_reductor(reductor, X_tr, X_va)
                m = clone(modelo).fit(X_tr, y_tr)
                aucs.append(roc_auc_score(y_va, m.predict_proba(X_va)[:, 1]))
            puntajes[nombre] = float(np.mean(aucs))

        elegido = max(puntajes, key=puntajes.get)

        # --- evaluación con el ganador, reentrenado con todo el train ---
        X_tr = pd.concat([dfsX[k] for k in otros], ignore_index=True)
        y_tr = pd.concat([dfsY[k] for k in otros], ignore_index=True)
        X_te = dfsX[test].reset_index(drop=True)
        y_te = dfsY[test].to_numpy()

        X_tr, X_te = _ajustar_reductor(candidatos[elegido], X_tr, X_te)
        m = clone(modelo).fit(X_tr, y_tr)
        proba = m.predict_proba(X_te)[:, 1]

        fila = {"escenario": test, "elegido": elegido}
        fila.update(_metricas(y_te, proba))
        fila.update({f"auc_{n}": v for n, v in puntajes.items()})
        filas.append(fila)

    return pd.DataFrame(filas).set_index("escenario").round(3)


def resumen_configuraciones(tablas, especificidades):
    """Una fila por configuración: tamaño, AUC, desvío, recall@5 y especificidad S0."""
    filas = []
    for nombre, tabla in tablas.items():
        filas.append({
            "configuración": nombre,
            "features": int(tabla.features.iloc[0]),
            "muestras": int(tabla.n.sum()),
            "AUC medio": tabla.auc.mean(),
            "desvío": tabla.auc.std(),
            "recall@5": tabla.recall_5.mean(),
            "espec S0 @TPR95": especificidades[nombre],
        })
    return pd.DataFrame(filas).set_index("configuración").round(3)


def rf_block_logo(X, y, grupos, reductor=GroupedPCA):
    """BlockPCA ajustado dentro de cada fold LOSO; un Random Forest por fold."""
    y = np.asarray(y).ravel()
    grupos = np.asarray(grupos)

    filas = []
    for fold, (tr, te) in enumerate(
            LeaveOneGroupOut().split(X, y, groups=grupos), start=1):
        red = reductor().fit(X.iloc[tr])
        X_tr, X_te = red.transform(X.iloc[tr]), red.transform(X.iloc[te])
        rf = RandomForestClassifier(**PARAMS_RF).fit(X_tr, y[tr])
        proba = rf.predict_proba(X_te)[:, 1]

        fila = {"fold": fold, "escenario": grupos[te][0], "features": X_tr.shape[1]}
        fila["accuracy_train"] = rf.score(X_tr, y[tr])
        fila.update(_metricas(y[te], proba))
        filas.append(fila)

    tabla = pd.DataFrame(filas).set_index("fold").round(3)
    tabla.loc["mean"] = tabla.mean(numeric_only=True).round(3)
    return tabla

def rf_logo(X, y, grupos):
    """Random Forest con LeaveOneGroupOut, sin reducción."""

    y = np.asarray(y).ravel()
    grupos = np.asarray(grupos)

    filas = []
    for fold, (tr, te) in enumerate(
            LeaveOneGroupOut().split(X, y, groups=grupos), start=1):
        rf = RandomForestClassifier(**PARAMS_RF).fit(X.iloc[tr], y[tr])
        proba = rf.predict_proba(X.iloc[te])[:, 1]

        fila = {"fold": fold, "escenario": grupos[te][0], "features": X.shape[1]}
        fila["accuracy_train"] = rf.score(X.iloc[tr], y[tr]) 
        fila.update(_metricas(y[te], proba))
        filas.append(fila)

    tabla = pd.DataFrame(filas).set_index("fold").round(3)
    tabla.loc["mean"] = tabla.mean(numeric_only=True).round(3)
    return tabla

def buscar_grid_rfe(X, y, grupos, clasificador, n_features,
                    step=5, espacio_modelo=None,
                    scoring="accuracy", cv=None, n_jobs=-1, verbose=1):
    """GridSearchCV sobre la cantidad de columnas de RFE, con LOSO.

    n_features: lista de valores para rfe__n_features_to_select.
    espacio_modelo: opcional, parámetros del clasificador con prefijo modelo__.
    """
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