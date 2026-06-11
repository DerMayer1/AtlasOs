"""Reference regime labels for validation (PRD R6).

Monthly ground-truth labels for the US, 2000-2024. Sources for the windows:
- Crisis windows follow NBER recession dating (GFC, COVID) plus the 2011
  US-downgrade/eurozone stress episode, which was not an NBER recession but is
  required by R6 as a known stress regime.
- Tightening windows follow Fed hiking cycles (2004-2006, 2015-2018 partial,
  2022-2023).
- Everything else is labeled expansion.

These labels are a judgment call and the report says so; the point is a fixed,
versioned benchmark, not revealed truth.
"""

from __future__ import annotations

import pandas as pd

CRISIS_WINDOWS = [
    ("2001-03", "2002-12"),  # dot-com recession (NBER: Mar-Nov 2001) + credit
    #                          stress through the Enron/WorldCom spread peak
    ("2008-01", "2009-06"),  # GFC (NBER: Dec 2007 - Jun 2009)
    ("2011-08", "2011-12"),  # US downgrade / eurozone stress
    ("2020-02", "2020-05"),  # COVID shock (NBER: Feb - Apr 2020)
]

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
