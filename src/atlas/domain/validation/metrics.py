"""Validation metrics for regime and binary crisis models."""

from __future__ import annotations

import numpy as np
import pandas as pd

from atlas.domain.engines.impairment.regimes import REGIMES


def confusion_matrix(labels: pd.Series, predicted: pd.Series) -> pd.DataFrame:
    """Rows = reference label, columns = predicted regime, values = months."""
    cm = pd.crosstab(labels, predicted, dropna=False)
    return cm.reindex(index=list(REGIMES), columns=list(REGIMES), fill_value=0)


def accuracy(labels: pd.Series, predicted: pd.Series) -> float:
    return float((labels == predicted).mean())


def detection_lag_months(
    crisis_probs: pd.Series, window_start: str, threshold: float = 0.5, horizon: int = 12
) -> int | None:
    """Months from the crisis window start until P(crisis) first crosses the
    threshold. None = never detected within `horizon` months. Note: monthly
    data bounds resolution at one month (see limitations)."""
    start = pd.Period(window_start, freq="M").to_timestamp(how="end")
    window = crisis_probs.loc[crisis_probs.index >= start.normalize()].iloc[:horizon]
    hits = window[window >= threshold]
    if hits.empty:
        return None
    first = hits.index[0]
    return (first.year - start.year) * 12 + (first.month - start.month)


def average_precision(labels: pd.Series, probabilities: pd.Series) -> float:
    """Area under the precision-recall step curve (average precision)."""
    aligned = pd.concat([labels.rename("y"), probabilities.rename("p")], axis=1).dropna()
    if aligned.empty or int(aligned["y"].sum()) == 0:
        return 0.0
    ranked = aligned.sort_values("p", ascending=False)
    positives = ranked["y"].astype(int).to_numpy()
    precision_at_rank = np.cumsum(positives) / np.arange(1, len(positives) + 1)
    return float((precision_at_rank * positives).sum() / positives.sum())


def binary_metrics(
    labels: pd.Series,
    predictions: pd.Series,
    probabilities: pd.Series | None = None,
) -> dict[str, float]:
    probability_values = (
        probabilities.rename("prob")
        if probabilities is not None
        else predictions.rename("prob")
    )
    aligned = pd.concat(
        [
            labels.rename("y"),
            predictions.rename("pred"),
            probability_values,
        ],
        axis=1,
    ).dropna()
    y = aligned["y"].astype(int)
    pred = aligned["pred"].astype(int)
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    years = max(1, aligned.index.to_period("Y").nunique())
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "pr_auc": average_precision(y, aligned["prob"]),
        "brier": float(((aligned["prob"] - y) ** 2).mean()),
        "false_alerts_per_year": fp / years,
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "tn": float(tn),
    }


def select_threshold(
    labels: pd.Series,
    probabilities: pd.Series,
    min_recall: float = 0.60,
) -> float:
    """Choose the highest-precision training threshold meeting a recall floor."""
    aligned = pd.concat([labels.rename("y"), probabilities.rename("p")], axis=1).dropna()
    candidates = sorted(set(np.linspace(0.05, 0.95, 91)).union(aligned["p"].tolist()))
    scored: list[tuple[bool, float, float, float]] = []
    for threshold in candidates:
        pred = (aligned["p"] >= threshold).astype(int)
        metrics = binary_metrics(aligned["y"], pred, aligned["p"])
        scored.append(
            (
                metrics["recall"] >= min_recall,
                metrics["precision"],
                metrics["recall"],
                float(threshold),
            )
        )
    eligible = [row for row in scored if row[0]]
    pool = eligible or scored
    return max(pool, key=lambda row: (row[1], row[2], row[3]))[3]


def calibration_table(
    labels: pd.Series,
    probabilities: pd.Series,
    bins: int = 5,
) -> pd.DataFrame:
    aligned = pd.concat([labels.rename("actual"), probabilities.rename("probability")], axis=1)
    aligned = aligned.dropna()
    aligned["bin"] = pd.cut(
        aligned["probability"],
        bins=np.linspace(0.0, 1.0, bins + 1),
        include_lowest=True,
    )
    return aligned.groupby("bin", observed=False).agg(
        observations=("actual", "size"),
        mean_probability=("probability", "mean"),
        crisis_rate=("actual", "mean"),
    )
