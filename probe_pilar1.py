"""Probe descartable — Pilar I: ¿la clusterización agrupa física o tiempo?

Responde UNA pregunta: si al pasar de los features crudos a los invariantes
ciberfísicos, el agrupamiento de KMeans deja de alinearse con el tiempo.

NO toca el notebook. Corre como script suelto:

    python probe_pilar1.py          # desde la raíz del repo
    .venv/bin/python probe_pilar1.py

Salida: una tabla con ARI / NMI / V de Cramér entre las etiquetas de KMeans y
``bloque_temporal`` (el horizonte partido en K bloques cronológicos iguales),
para cada conjunto de features y varios K.

Comparación:
- crudo        : 132 features en nivel (lo que sale de ``eliminar_columnas``)
- rango        : rango móvil de 120 s (lo que hoy usa el detector del notebook)
- diferencias  : primeras diferencias  ΔX_t = X_t - X_{t-1}
- invariantes  : ΔSOC + residuo de potencia aparente + desequilibrio interfase
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# --- Entorno: misma resolución de rutas que el notebook -------------------
RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "Colab"))

from src2.data import eliminar_columnas, imputar_media  # noqa: E402
from src2.features import rango_movil  # noqa: E402

SEED = 42
METROS = [
    "BSS-Inverter-AC-Meter",
    "Load-A-AC-Meter",
    "Load-B-AC-Meter",
    "PV-Inverter-AC-Meter",
    "Substation-AC-Meter",
]
KS = [3, 5, 8]


# --- 1. Transformaciones ciberfísicas ------------------------------------
def invariantes_fisicas(df: pd.DataFrame) -> pd.DataFrame:
    """ΔSOC + S_error + desequilibrio interfase. 11 features, sin nivel absoluto."""
    out = pd.DataFrame(index=df.index)

    # ΔSOC = |SOC reportado - SOC referencia| (1)
    out["dsoc"] = (
        df["Battery-SOC-Reported.soc_value"]
        - df["Battery-SOC-Reference.soc_value"]
    ).abs()

    for m in METROS:
        # Residuo de potencia aparente: sqrt(P² + Q²) - S_medido (5)
        p, q, s = df[f"{m}.p_sum3"], df[f"{m}.q_sum3"], df[f"{m}.s_sum3"]
        out[f"{m}__serror"] = np.sqrt(p**2 + q**2) - s

        # Desequilibrio interfase: max |V_fase_i - V_fase_j| (5)
        u1, u2, u3 = df[f"{m}.uln1"], df[f"{m}.uln2"], df[f"{m}.uln3"]
        out[f"{m}__imbalance"] = pd.concat(
            [(u1 - u2).abs(), (u2 - u3).abs(), (u3 - u1).abs()], axis=1
        ).max(axis=1)

    return out


# --- 2. Preparación (idéntica a ``preparar`` del notebook, sección 6) ------
def preparar(X: pd.DataFrame) -> np.ndarray:
    pipe = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        PCA(n_components=0.95, random_state=SEED),
    )
    return pipe.fit_transform(X)


# --- 3. Test de contingencia cronométrica (K-bloques) ----------------------
def kblock(Z: np.ndarray, k: int) -> dict:
    """ARI / NMI / V de Cramér entre las etiquetas de KMeans y K bloques temporales."""
    n = len(Z)
    etiquetas = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(Z)

    posicion = np.linspace(0.0, 1.0, n)
    bloque = np.minimum((posicion * k).astype(int), k - 1)

    tabla = pd.crosstab(etiquetas, bloque)
    chi2 = chi2_contingency(tabla.values, correction=False)[0]
    cramer = float(np.sqrt(chi2 / (n * (min(tabla.shape) - 1))))

    return {
        "ari": float(adjusted_rand_score(bloque, etiquetas)),
        "nmi": float(normalized_mutual_info_score(bloque, etiquetas)),
        "cramer": cramer,
    }


# --- 4. Carga y armado de los conjuntos de features ------------------------
def cargar_s0() -> pd.DataFrame:
    df = pd.read_csv(RAIZ / "datasets" / "datasetS0.csv")
    df = imputar_media(eliminar_columnas(df))
    return df.drop(columns=["attack_active"])  # S0 es 100% benigno


def main() -> None:
    s0 = cargar_s0()

    crudo = s0.copy()
    rango = rango_movil(s0, 120)
    diferencias = s0.diff().iloc[1:]               # n-1 filas
    invariantes = invariantes_fisicas(s0).iloc[1:]  # n-1 para alinear

    conjuntos = {
        "crudo": crudo.iloc[1:],            # n-1 para alinear con diff
        "rango": rango.iloc[1:],
        "diferencias": diferencias,
        "invariantes": invariantes,
    }

    filas = []
    for nombre, X in conjuntos.items():
        Z = preparar(X)
        fila = {"conjunto": nombre, "features": X.shape[1]}
        for k in KS:
            r = kblock(Z, k)
            fila[f"ARI k={k}"] = round(r["ari"], 3)
            fila[f"NMI k={k}"] = round(r["nmi"], 3)
            fila[f"Cramer k={k}"] = round(r["cramer"], 3)
        filas.append(fila)

    tabla = pd.DataFrame(filas).set_index("conjunto")
    print("\nS0: ARI / NMI / V de Cramér entre KMeans y bloque_temporal")
    print("(valores altos = la clusterización sigue al tiempo; bajos = desacoplada)")
    print(tabla.to_string())


if __name__ == "__main__":
    main()
