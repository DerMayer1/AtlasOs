"""Synthetic macro data for demos and tests. Real FRED ingestion lands in
Phase 2 behind the same snapshot discipline."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_macro_frame(seed: int = 42, periods: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2015-01-31", periods=periods, freq="ME")
    return pd.DataFrame(
        {
            "fed_funds": np.clip(rng.normal(2.5, 1.5, periods), 0, None),
            "baa_aaa_spread": np.clip(rng.normal(1.0, 0.4, periods), 0.1, None),
            "t10y2y": rng.normal(0.8, 0.9, periods),
            "cpi_yoy": rng.normal(2.5, 1.8, periods),
            "unemployment": np.clip(rng.normal(5.0, 1.5, periods), 2.5, None),
        },
        index=idx,
    )
