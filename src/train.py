"""Command line entry point for the Data4Cyber experiments.

Examples
--------
Smoke test (one held-out scenario, one model):
    python -m src.train --only S6 --models rf

Binary LOSO (3 models x 8 folds):
    python -m src.train --task binary --out resultados/binario.csv

Binary LOSO with the position-only control:
    python -m src.train --task binary --baseline position --out resultados/binario.csv

Binary LOSO after removing slow drift (60 s rolling mean):
    python -m src.train --task binary --detrend mean --window 60

Attack-family LOSO (strict transfer test):
    python -m src.train --task family --out resultados/familias_loso.csv

Attack-family stratified 5-fold (all families present in training):
    python -m src.train --task family --split strat --out resultados/familias_strat.csv
"""

from __future__ import annotations

import argparse
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder

from .data import SCENARIOS, build_matrices, load_all
from .features import METHODS as DETREND_METHODS
from .features import detrend as detrend_frame
from .pipeline import MODEL_NAMES, balanced_weights, build_pipeline, make_model

FAMILIES: tuple[str, ...] = ("benign", "modbus_pv", "modbus_bss", "arp", "mqtt")


def recall_at_fpr(y_true, y_score, target_fpr: float) -> float:
    """TPR at a fixed false-positive rate, read off the test ROC.

    This summarises the ROC curve at an operating point an operator could
    tolerate; it is not a threshold tuned on the test set.
    """
    if y_score is None or len(np.unique(y_true)) < 2:
        return float("nan")
    fpr, tpr, _ = roc_curve(y_true, y_score)
    return float(np.interp(target_fpr, fpr, tpr))


def binary_report(y_true, y_pred, y_score=None) -> dict:
    """Per-class report. Undefined values stay NaN instead of being invented."""
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)

    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))

    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    specificity = tn / (tn + fp) if (tn + fp) else float("nan")
    if np.isnan(precision) or np.isnan(recall) or (precision + recall) == 0:
        f1 = float("nan")
    else:
        f1 = 2 * precision * recall / (precision + recall)

    accuracy = (tp + tn) / len(y_true)
    parts = [v for v in (recall, specificity) if not np.isnan(v)]
    balanced = float(np.mean(parts)) if parts else float("nan")

    auc = float("nan")
    if y_score is not None and len(np.unique(y_true)) == 2:
        auc = float(roc_auc_score(y_true, y_score))

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "recall": recall,
        "precision": precision,
        "specificity": specificity,
        "f1": f1,
        "accuracy": accuracy,
        "balanced_acc": balanced,
        "roc_auc": auc,
        "recall_at_fpr1": recall_at_fpr(y_true, y_score, 0.01),
        "recall_at_fpr5": recall_at_fpr(y_true, y_score, 0.05),
    }


def family_report(y_true, y_pred) -> dict:
    """Multiclass report over the families present in this fold.

    A held-out scenario only contains its own family plus benign rows, so
    averaging over all five families would cap macro-F1 at 2/5 no matter how
    good the model is. Macro-F1 is averaged over the classes actually present.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    present = [family for family in FAMILIES if np.any(y_true == family)]
    cm = confusion_matrix(y_true, y_pred, labels=present)

    recalls = {}
    for index, family in enumerate(present):
        support = int(cm[index].sum())
        recalls[f"recall_{family}"] = (
            float(cm[index, index] / support) if support else float("nan")
        )

    return {
        "accuracy": float(np.mean(y_true == y_pred)),
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=present, average="macro", zero_division=0)
        ),
        "n_classes": len(present),
        **recalls,
    }


def _scores(pipe, X) -> np.ndarray:
    """Continuous score for the positive class, model-agnostic."""
    final = pipe[-1]
    if hasattr(final, "predict_proba"):
        return pipe.predict_proba(X)[:, 1]
    return pipe.decision_function(X)


def _position_baseline(position, target, train_index, test_index, seed) -> dict:
    """How much a model can decide from the clock alone.

    A Random Forest fitted on the relative position inside the scenario, with
    the same preprocessing and class weights as the main models. It is the
    control row: any model that does not beat it is only reading the clock.
    """
    pipe = build_pipeline(make_model("rf", seed))
    pipe.fit(
        position.to_frame().iloc[train_index],
        target.iloc[train_index],
        model__sample_weight=balanced_weights(target.iloc[train_index]),
    )
    score = _scores(pipe, position.to_frame().iloc[test_index])
    truth = np.asarray(target.iloc[test_index])

    auc = float("nan")
    if len(np.unique(truth)) == 2:
        auc = float(roc_auc_score(truth, score))

    pred = (score >= 0.5).astype(int)
    tn = int(np.sum((pred == 0) & (truth == 0)))
    fp = int(np.sum((pred == 1) & (truth == 0)))
    specificity = tn / (tn + fp) if (tn + fp) else float("nan")

    return {"baseline_auc": auc, "baseline_specificity": specificity}


def _folds(matrices, split: str, seed: int):
    """Yield (name, train_index, test_index) for the requested protocol."""
    if split == "loso":
        for held in SCENARIOS:
            test_index = np.where(matrices.scenario.to_numpy() == held)[0]
            train_index = np.where(matrices.scenario.to_numpy() != held)[0]
            yield held, train_index, test_index
        return

    if split == "strat":
        # Keep every scenario x family combination present in every fold, so the
        # multiclass question is answerable at all. Disclosed as non-transfer.
        strat = matrices.scenario + "|" + matrices.y_family
        splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        for number, (train_index, test_index) in enumerate(
            splitter.split(matrices.X, strat), start=1
        ):
            yield f"fold{number}", train_index, test_index
        return

    raise ValueError(f"unknown split {split!r}; expected 'loso' or 'strat'")


def run(
    task: str = "binary",
    split: str = "loso",
    only: list[str] | None = None,
    models: tuple[str, ...] = MODEL_NAMES,
    balanced: bool = True,
    include_price: bool = False,
    detrend: str = "none",
    window: int = 60,
    baseline: str | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Evaluate the three models under the requested task and split protocol."""
    if task not in {"binary", "family"}:
        raise ValueError(f"unknown task {task!r}")
    if baseline not in (None, "position"):
        raise ValueError(f"unknown baseline {baseline!r}; expected None or 'position'")
    if only and split == "loso":
        allowed = set(only)
    else:
        allowed = None

    warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
    matrices = build_matrices(load_all(), include_price=include_price)
    X = matrices.X
    if detrend != "none":
        X = detrend_frame(X, matrices.scenario, method=detrend, window=window)
    target = matrices.y_binary if task == "binary" else matrices.y_family
    print(
        f"task={task} split={split} rows={len(X):,} "
        f"features={X.shape[1]} price={'on' if include_price else 'off'} "
        f"balanced={balanced} detrend={detrend}"
        + (f" window={window}s" if detrend not in ("none", "diff") else "")
    )

    rows = []
    for name, train_index, test_index in _folds(matrices, split, seed):
        if allowed is not None and name not in allowed:
            continue

        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = target.iloc[train_index], target.iloc[test_index]

        extra = {}
        if baseline == "position" and task == "binary":
            extra = _position_baseline(
                matrices.position, target, train_index, test_index, seed
            )

        if task == "family":
            encoder = LabelEncoder().fit(y_train)
            y_train_fit = encoder.transform(y_train)
        else:
            encoder = None
            y_train_fit = y_train

        for model_name in models:
            started = time.time()
            pipe = build_pipeline(make_model(model_name, seed=seed))
            fit_params = {}
            if balanced:
                fit_params["model__sample_weight"] = balanced_weights(y_train_fit)

            pipe.fit(X_train, y_train_fit, **fit_params)
            raw = pipe.predict(X_test)
            pred = encoder.inverse_transform(raw) if encoder is not None else raw

            if task == "binary":
                report = binary_report(y_test, pred, _scores(pipe, X_test))
                print(
                    f"  {name:6s} {model_name:4s} auc={report['roc_auc']:.3f} "
                    f"r@1%fpr={report['recall_at_fpr1']:.3f} "
                    f"r@5%fpr={report['recall_at_fpr5']:.3f} "
                    f"recall={report['recall']:.3f} spec={report['specificity']:.3f} "
                    f"({time.time() - started:.1f}s)"
                )
            else:
                report = family_report(y_test, pred)
                print(
                    f"  {name:6s} {model_name:4s} macro_f1={report['macro_f1']:.3f} "
                    f"acc={report['accuracy']:.3f} ({time.time() - started:.1f}s)"
                )

            row = {"split": split, "fold": name, "model": model_name, "n_test": len(y_test)}
            if task == "binary":
                row["n_pos"] = int(np.sum(y_test))
                row["n_neg"] = int(len(y_test) - np.sum(y_test))
            row.update(report)
            row.update(extra)
            row["seconds"] = round(time.time() - started, 1)
            rows.append(row)

    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=("binary", "family"), default="binary")
    parser.add_argument("--split", choices=("loso", "strat"), default="loso")
    parser.add_argument("--only", nargs="*", default=None, help="held-out scenarios, e.g. S6")
    parser.add_argument("--models", nargs="*", default=list(MODEL_NAMES), choices=MODEL_NAMES)
    parser.add_argument("--no-balance", action="store_true", help="disable sample weights")
    parser.add_argument(
        "--include-price", action="store_true", help="reproduce the leakage negative control"
    )
    parser.add_argument(
        "--detrend",
        choices=DETREND_METHODS,
        default="none",
        help="per-scenario drift removal; 'none' keeps the raw levels",
    )
    parser.add_argument(
        "--window", type=int, default=60, help="rolling window in rows (one row = one second)"
    )
    parser.add_argument(
        "--baseline",
        choices=("none", "position"),
        default="none",
        help="add the position-only control to each binary fold",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    result = run(
        task=args.task,
        split=args.split,
        only=args.only,
        models=tuple(args.models),
        balanced=not args.no_balance,
        include_price=args.include_price,
        detrend=args.detrend,
        window=args.window,
        baseline=None if args.baseline == "none" else args.baseline,
        seed=args.seed,
    )

    if args.out:
        result.to_csv(args.out, index=False)
        print(f"\nwrote {args.out}")

    if args.task == "binary":
        columns = [
            "fold",
            "model",
            "roc_auc",
            "recall_at_fpr1",
            "recall_at_fpr5",
            "recall",
            "specificity",
            "n_pos",
            "n_neg",
        ]
        for extra in ("baseline_auc", "baseline_specificity"):
            if extra in result.columns:
                columns.append(extra)
    else:
        columns = ["fold", "model", "macro_f1", "accuracy", "n_test"]

    print("\n" + result[columns].round(3).to_string(index=False))

    if args.task == "binary":
        attack = result[result["fold"] != "S0"]
        s0 = result[result["fold"] == "S0"]
        print("\nresumen: AUC media en folds de ataque + especificidad en S0")
        for model_name in result["model"].unique():
            model_attack = attack[attack["model"] == model_name]
            model_s0 = s0[s0["model"] == model_name]
            auc = model_attack["roc_auc"].mean()
            spec = model_s0["specificity"].mean()
            base = model_attack.get("baseline_auc", pd.Series(dtype=float)).mean()
            print(
                f"  {model_name:4s} auc_media={auc:.3f} spec_S0={spec:.3f} "
                f"baseline_auc={base:.3f}"
            )

    if args.split == "strat":
        numeric = result.select_dtypes(include=[np.number]).columns.drop("fold", errors="ignore")
        summary = result.groupby("model")[list(numeric)].agg(["mean", "std"])
        print("\nresumen por modelo (media y desvio entre folds):")
        print(summary.round(3).to_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
