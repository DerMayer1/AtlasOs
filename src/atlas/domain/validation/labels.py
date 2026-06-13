"""Versioned reference labels used by model validation.

Two binary definitions are intentionally kept separate:

``strict``
    Official NBER recessions. This is the primary model-training target.
``stress``
    Broader market-stress windows, including 2011 and extended credit stress.

The legacy three-regime labels remain available for the HMM report and shock
calibration. Keeping the definitions explicit prevents a model improvement from
being manufactured by silently changing what "crisis" means.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd

STRICT_CRISIS_WINDOWS = [
    ("1990-07", "1991-03"),  # NBER recession
    ("2001-03", "2001-11"),  # NBER recession
    ("2007-12", "2009-06"),  # NBER recession
    ("2020-02", "2020-04"),  # NBER recession
]

STRESS_CRISIS_WINDOWS = [
    ("1990-07", "1991-03"),
    ("2001-03", "2002-12"),  # dot-com recession (NBER: Mar-Nov 2001) + credit
    #                          stress through the Enron/WorldCom spread peak
    ("2008-01", "2009-06"),  # GFC (NBER: Dec 2007 - Jun 2009)
    ("2011-08", "2011-12"),  # US downgrade / eurozone stress
    ("2020-02", "2020-05"),  # COVID shock (NBER: Feb - Apr 2020)
]

# Backward-compatible name used by the three-regime report and calibration.
CRISIS_WINDOWS = STRESS_CRISIS_WINDOWS

TIGHTENING_WINDOWS = [
    ("2004-07", "2006-08"),
    ("2017-01", "2018-12"),
    ("2022-03", "2023-09"),
]


def reference_labels(index: pd.DatetimeIndex) -> pd.Series:
    labels = pd.Series("expansion", index=index, name="label")
    for start, end in TIGHTENING_WINDOWS:
        labels.loc[start:end] = "tightening"
    for start, end in CRISIS_WINDOWS:  # crisis wins over tightening
        labels.loc[start:end] = "crisis"
    return labels


def binary_crisis_labels(
    index: pd.DatetimeIndex,
    definition: Literal["strict", "stress"] = "strict",
    horizon_months: int = 0,
) -> pd.Series:
    """Return a binary crisis target on a monthly index.

    ``horizon_months`` shifts crisis windows earlier and is reserved for future
    early-warning experiments. The production validation uses ``0`` so it
    measures contemporaneous detection without changing the target.
    """
    if horizon_months < 0:
        raise ValueError("horizon_months must be >= 0")
    windows = STRICT_CRISIS_WINDOWS if definition == "strict" else STRESS_CRISIS_WINDOWS
    labels = pd.Series(0, index=index, dtype=int, name=f"crisis_{definition}")
    shift = pd.DateOffset(months=horizon_months)
    for start, end in windows:
        shifted_start = pd.Timestamp(start) - shift
        shifted_end = pd.Timestamp(end) - shift
        labels.loc[shifted_start.strftime("%Y-%m"):shifted_end.strftime("%Y-%m")] = 1
    return labels
