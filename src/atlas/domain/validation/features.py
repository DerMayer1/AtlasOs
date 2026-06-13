"""Causal feature engineering for crisis validation.

All transformations are backward-looking. CPI and unemployment are shifted by
one month to approximate their publication delay in a historical backtest.
Financial-market series are available within their observation month.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PUBLICATION_LAGS = {
    "cpi_yoy": 1,
    "unemployment": 1,
}


def apply_publication_lags(macro: pd.DataFrame) -> pd.DataFrame:
    """Return the data that would have been observable at each month-end."""
    out = macro.copy()
    for column, months in PUBLICATION_LAGS.items():
        if column in out:
            out[column] = out[column].shift(months)
    return out


def build_crisis_features(macro: pd.DataFrame) -> pd.DataFrame:
    """Build compact, interpretable backward-looking macro features."""
    required = {
        "fed_funds",
        "baa_aaa_spread",
        "t10y2y",
        "cpi_yoy",
        "unemployment",
    }
    missing = sorted(required.difference(macro.columns))
    if missing:
        raise ValueError(f"macro frame missing validation series: {missing}")

    data = apply_publication_lags(macro)
    features = pd.DataFrame(index=data.index)
    for column in sorted(required):
        features[column] = data[column]

    for months in (1, 3, 6):
        features[f"baa_aaa_spread_chg{months}"] = data["baa_aaa_spread"].diff(months)
    for months in (3, 6):
        features[f"fed_funds_chg{months}"] = data["fed_funds"].diff(months)
        features[f"t10y2y_chg{months}"] = data["t10y2y"].diff(months)
        features[f"cpi_yoy_chg{months}"] = data["cpi_yoy"].diff(months)
        features[f"unemployment_chg{months}"] = data["unemployment"].diff(months)
    features["unemployment_chg12"] = data["unemployment"].diff(12)

    if "vix" in data:
        features["vix"] = data["vix"]
        for months in (1, 3):
            features[f"vix_chg{months}"] = data["vix"].diff(months)

    return features.replace([np.inf, -np.inf], np.nan).astype(float)
