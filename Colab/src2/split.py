import numpy as np
import pandas as pd


def separar_variables(df):
    dfX = df.drop(["attack_active"],axis=1)
    dfY = df["attack_active"]
    return dfX, dfY

def aplanar_ventanas(dfX, y, ventana):
    """Devuelve la matriz aplanada y la etiqueta de la ultima fila de cada ventana."""
    X = dfX.to_numpy(dtype=np.float32)
    etiquetas = y.to_numpy()
    bloques = np.stack([X[i:i + ventana] for i in range(len(X) - ventana + 1)])
    columnas = [f"{canal}_t{paso}" for paso in range(ventana) for canal in dfX.columns]
    planas = bloques.reshape(len(bloques), -1)
    return pd.DataFrame(planas, columns=columnas), pd.Series(etiquetas[ventana - 1:], name="attack_active")

def aplanar_escenarios(dfsX, dfsY, ventana=20):
    """Aplana la ventana escenario por escenario y devuelve X e y alineados."""
    X, y = {}, {}
    for k in dfsX:
        X[k], y[k] = aplanar_ventanas(dfsX[k], dfsY[k], ventana)
    return X, y

def aplanar_df(X, y, ventana):
    """Aplana ventanas por escenario sobre (X con columna escenario, y) y devuelve (X_win, y_win)."""
    etiquetas_esc = X["escenario"].to_numpy()
    y = np.asarray(y).ravel()
    Xs = X.drop(columns=["escenario"])

    partes, ys = [], []
    for k in pd.unique(etiquetas_esc):
        idx = np.flatnonzero(etiquetas_esc == k)
        Xf, yf = aplanar_ventanas(Xs.iloc[idx], pd.Series(y[idx]), ventana)
        Xf.insert(0, "escenario", k)
        partes.append(Xf)
        ys.append(yf.to_numpy())

    return pd.concat(partes, ignore_index=True), pd.Series(np.concatenate(ys), name="attack_active")