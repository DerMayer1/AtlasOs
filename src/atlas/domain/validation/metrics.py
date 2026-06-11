"""Validation metrics: confusion matrix, detection lag, accuracy (PRD R6)."""

from __future__ import annotations

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
