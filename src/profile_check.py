"""How much of the result depends on the scenario profile.

``Profile.*`` holds ambient temperature, load, PV output and irradiance. Those
columns look like ordinary measurements, but in this dataset only ``S0`` was
recorded with the profile frozen: every strip is exactly constant there, while
every attack scenario shows a normal, similar dispersion.

That matters because a model can learn "profile still => benign" without
measuring anything electrical. This module quantifies it three ways:

1. How constant the profile is per scenario.
2. How much a single number (the moving range of the profile) separates
   scenarios, and how much it separates attacks inside a scenario.
3. What the chosen recipe loses when the seven profile columns are removed.

Run with: python -m src.profile_check
Writes resultados/perfil.csv.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .data import SCENARIOS, build_matrices, load_all
from .features import detrend
from .pipeline import balanced_weights, build_pipeline, make_model
from .reduce import corr_filter, physical_features
from .train import recall_at_fpr

WINDOW = 120
PROFILE = "Profile."


def loso_physical(X, y, scenario, drop=(), model_name="rf"):
    """LOSO on the chosen recipe, optionally dropping columns after the filter.

    The correlation filter is fitted per fold on the training rows only, then
    ``drop`` is removed, exactly as the ablation reported in the notebook did.
    """
    aucs, recalls_5, recalls_1, kept = [], [], [], []
    spec_s0 = float("nan")
    for held in SCENARIOS:
        test = (scenario == held).to_numpy()
        train = ~test
        columns = [c for c in corr_filter(X.loc[train]) if c not in drop]
        Xtr, Xte = X.loc[train, columns], X.loc[test, columns]
        ytr, yte = y.loc[train], y.loc[test].to_numpy()

        model = build_pipeline(make_model(model_name))
        model.fit(Xtr, ytr, model__sample_weight=balanced_weights(ytr))
        score = model.predict_proba(Xte)[:, 1]
        kept.append(len(columns))

        if len(np.unique(yte)) == 2:
            aucs.append(float(roc_auc_score(yte, score)))
            recalls_5.append(recall_at_fpr(yte, score, 0.05))
            recalls_1.append(recall_at_fpr(yte, score, 0.01))
        if held == "S0":
            spec_s0 = float(((score >= 0.5).astype(int) == 0).mean())

    return {
        "auc_mean": float(np.mean(aucs)),
        "spec_S0": spec_s0,
        "n_features": float(np.mean(kept)),
        "recall_5": float(np.mean(recalls_5)),
        "recall_1": float(np.mean(recalls_1)),
    }


def main() -> int:
    warnings.filterwarnings("ignore")
    matrices = build_matrices(load_all())
    X = detrend(matrices.X, matrices.scenario, method="range", window=WINDOW)
    y, scenario = matrices.y_binary, matrices.scenario

    profile = [c for c in X.columns if c.startswith(PROFILE)]
    moving_range = X[profile].sum(axis=1)
    attack_scenes = (scenario != "S0").to_numpy()

    rows: list[dict] = []

    # 1. The profile is frozen in S0 and moving everywhere else.
    for column in ("Profile.ambient_temperature", "Profile.load2_kw", "Profile.total_irradiance"):
        for held in SCENARIOS:
            rows.append(
                {
                    "medida": "desvio_por_escenario",
                    "detalle": f"{column} @ {held}",
                    "valor": round(float(X.loc[scenario == held, column].std()), 3),
                }
            )

    # 2. One number: does the profile move?
    rows.append(
        {
            "medida": "auc_perfil_s0_vs_ataques",
            "detalle": "rango movil del perfil, S0 contra S1..S6",
            "valor": round(float(roc_auc_score(attack_scenes.astype(int), moving_range)), 4),
        }
    )
    rows.append(
        {
            "medida": "auc_perfil_dentro_de_escenario",
            "detalle": "S1..S6, ataque contra benigno",
            "valor": round(float(roc_auc_score(y[attack_scenes], moving_range[attack_scenes])), 4),
        }
    )
    rows.append(
        {
            "medida": "fraccion_perfil_quieto",
            "detalle": "S0",
            "valor": round(float((moving_range[~attack_scenes] == 0).mean()), 4),
        }
    )
    for label, mask in (("ataque en S1..S6", y[attack_scenes] == 1), ("benigno en S1..S6", y[attack_scenes] == 0)):
        rows.append(
            {
                "medida": "fraccion_perfil_quieto",
                "detalle": label,
                "valor": round(float((moving_range[attack_scenes][mask] == 0).mean()), 4),
            }
        )

    # 3. Ablation on the chosen recipe.
    physical = physical_features(X)
    for nombre, drop in (("con_perfil", ()), ("sin_perfil", tuple(profile))):
        result = loso_physical(physical, y, scenario, drop=drop)
        for key, value in result.items():
            rows.append({"medida": f"loso_{key}", "detalle": nombre, "valor": round(value, 4)})
        print(f"{nombre}: {result}", flush=True)

    table = pd.DataFrame(rows)
    table.to_csv("resultados/perfil.csv", index=False)
    print("\nwrote resultados/perfil.csv")
    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
