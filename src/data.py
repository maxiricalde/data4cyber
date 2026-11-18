"""Data loading and matrix construction for the Data4Cyber final project.

All eight scenario tables share the same 155 columns. S6 adds
``MQTT-Price-Signal.event``, which is a leakage column and is dropped like the
rest of the annotation layer.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

SCENARIOS: tuple[str, ...] = ("S0", "S1", "S1alt", "S2", "S3", "S4", "S5", "S6")

# Attack family per scenario. Used as the multiclass target: every attack row
# inherits the family of its scenario, every benign row is "benign".
FAMILY: dict[str, str] = {
    "S0": "benign",
    "S1": "modbus_pv",
    "S1alt": "modbus_pv",
    "S2": "modbus_bss",
    "S3": "arp",
    "S4": "arp",
    "S5": "arp",
    "S6": "mqtt",
}

# Annotation layer: never a feature.
LABEL_COLS: tuple[str, ...] = ("attack_active", "attack_phase", "attack_phase_all")
# Wall-clock columns: the temporal index is not a measurement.
TIME_COLS: tuple[str, ...] = ("timestamp", "Profile.timestamp")
# Textual event log only present in S6.
LEAK_COLS: tuple[str, ...] = ("MQTT-Price-Signal.event",)
PRICE_COL = "MQTT-Price-Signal.price_eur_per_kwh"

# Override on Colab, e.g. DATA4CYBER_BASE=/content/drive/MyDrive/TrabajoFinal/datasets
DEFAULT_BASE = os.environ.get("DATA4CYBER_BASE", "datasets")


def load_scenario(name: str, base: str = DEFAULT_BASE) -> pd.DataFrame:
    """Read one scenario CSV and tag every row with its scenario id."""
    path = f"{base}/dataset{name}.csv"
    return pd.read_csv(path).assign(scenario=name)


def load_all(base: str = DEFAULT_BASE) -> pd.DataFrame:
    """Concatenate the eight scenarios into one frame preserving row order."""
    return pd.concat([load_scenario(name, base) for name in SCENARIOS], ignore_index=True)


@dataclass
class Matrices:
    """Feature matrix and targets, all sharing the same row index."""

    X: pd.DataFrame
    y_binary: pd.Series
    y_family: pd.Series
    y_phase: pd.Series
    scenario: pd.Series
    position: pd.Series


def _drop_leaks(df: pd.DataFrame, include_price: bool) -> pd.DataFrame:
    drop = [c for c in LABEL_COLS + TIME_COLS + LEAK_COLS if c in df.columns]
    # Device clocks and per-scenario phase codes.
    drop += [c for c in df.columns if c.endswith((".realtime", ".phase_seq"))]
    if not include_price:
        drop.append(PRICE_COL)
    return df.drop(columns=[c for c in drop if c in df.columns])


def build_matrices(df: pd.DataFrame, include_price: bool = False) -> Matrices:
    """Build X and the three targets from a concatenated scenario frame.

    ``include_price`` exists only to reproduce the leakage negative control from
    the S6 EDA. The baseline used everywhere else keeps it out.
    """
    y_binary = df["attack_active"].astype(int).rename("attack_active")

    family = df["scenario"].map(FAMILY).fillna("benign")
    y_family = family.where(y_binary == 1, "benign").rename("family")

    y_phase = df["attack_phase"].fillna("normal").rename("phase")

    X = _drop_leaks(df, include_price)
    X = X.drop(columns=[c for c in ("scenario", "attack_active") if c in X.columns])

    non_numeric = [c for c in X.columns if not pd.api.types.is_numeric_dtype(X[c])]
    if non_numeric:
        raise TypeError(f"unexpected non-numeric feature columns: {non_numeric}")

    # A single inf would poison median imputation and the scaler.
    X = X.replace([np.inf, -np.inf], np.nan)

    # Relative position inside each scenario: 0 at the first row, 1 at the last.
    # This is the clock the models can exploit; it is only the control variable
    # of the position baseline, never a feature of the main matrix.
    sizes = df.groupby("scenario")["scenario"].transform("size")
    position = (df.groupby("scenario").cumcount() / (sizes - 1)).rename("position")

    return Matrices(
        X=X,
        y_binary=y_binary,
        y_family=y_family,
        y_phase=y_phase,
        scenario=df["scenario"].rename("scenario"),
        position=position,
    )
