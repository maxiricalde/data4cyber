

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display


def plot_ataques_benignos(df):
    
    resumen = (
        df.groupby("escenario", sort=False)["attack_active"]
        .agg(ataque="sum", benigno=lambda s: (~s).sum())
        .astype(int)
    )
    resumen["filas"] = resumen.sum(axis=1)


    barras = resumen[["benigno", "ataque"]].copy()
    barras.loc["total"] = barras.sum()
    barras.plot.bar(
        stacked=True, color=["tab:green", "tab:red"], figsize=(9, 3.5)
    )
    plt.title("Filas benignas y de ataque por escenario")
    plt.xlabel("escenario")
    plt.ylabel("filas")
    plt.xticks(rotation=0)
    plt.legend(["benigno", "ataque"])
    plt.show()
