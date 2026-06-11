"""Macro regime classification — Phase 0 deterministic baseline.

Three regimes: expansion / tightening / crisis. The Phase 0 model scores the
latest observation of each macro series as a z-score against its own history
and maps scores to regime probabilities via a fixed, documented weight matrix
and a softmax. It is deliberately simple, fully deterministic and replaceable:
the Phase 2 HMM will implement the same function signature, and the
validation report (PRD R6) will benchmark both.

Expected snapshot table "macro": index = dates, columns =
fed_funds, baa_aaa_spread, t10y2y, cpi_yoy, unemployment.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REGIMES = ("expansion", "tightening", "crisis")

REQUIRED_SERIES = ("fed_funds", "baa_aaa_spread", "t10y2y", "cpi_yoy", "unemployment")

# Rows: regimes; columns: series in REQUIRED_SERIES order.
# Signs encode direction: e.g. a wide credit spread (high z) loads on crisis,
# an inverted curve (low t10y2y z) loads on tightening/crisis.
_WEIGHTS = np.array(
    [
        #  ff   spread  curve   cpi    unemp
        [-0.3, -1.0, 0.8, -0.3, -0.8],  # expansion
        [1.0, 0.2, -0.8, 1.0, -0.2],  # tightening
        [0.2, 1.4, -0.6, 0.2, 1.2],  # crisis
    ]
)


def regime_probabilities(macro: pd.DataFrame) -> pd.Series:
    missing = [c for c in REQUIRED_SERIES if c not in macro.columns]
    if missing:
        raise ValueError(f"macro table missing required series: {missing}")
    if len(macro) < 24:
        raise ValueError("macro table needs at least 24 observations to compute z-scores")

    values = macro[list(REQUIRED_SERIES)].astype(float)
    if values.isna().any().any():
        raise ValueError("macro table contains NaNs; ingestion must fail loudly upstream")

    mean = values.mean()
    std = values.std(ddof=0).replace(0.0, 1.0)
    z = ((values.iloc[-1] - mean) / std).to_numpy()

    scores = _WEIGHTS @ z
    scores = scores - scores.max()  # numerical stability
    probs = np.exp(scores) / np.exp(scores).sum()
    return pd.Series(probs, index=list(REGIMES), name="probability")
