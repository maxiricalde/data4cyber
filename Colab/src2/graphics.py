"""Plots for the EDA: label balance per scenario."""

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display


def plot_ataques_benignos(dfs):
    """Table and stacked bars of benign and attack rows per scenario.

    Each DataFrame in `dfs` must have the boolean `attack_active` column.
    """
    resumen = pd.DataFrame(
        {
            "ataque": {k: int(df["attack_active"].sum()) for k, df in dfs.items()},
            "benigno": {k: int((~df["attack_active"]).sum()) for k, df in dfs.items()},
        }
    )
    resumen["filas"] = resumen.sum(axis=1)
    display(resumen)

    resumen[["benigno", "ataque"]].plot.bar(
        stacked=True, color=["tab:green", "tab:red"], figsize=(9, 3.5)
    )
    plt.title("Filas benignas y de ataque por escenario")
    plt.xlabel("escenario")
    plt.ylabel("filas")
    plt.xticks(rotation=0)
    plt.legend(["benigno", "ataque"])
    plt.show()
