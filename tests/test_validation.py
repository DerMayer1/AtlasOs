import pandas as pd

from atlas.domain.validation.labels import reference_labels
from atlas.domain.validation.metrics import accuracy, confusion_matrix, detection_lag_months


def test_reference_labels_windows():
    idx = pd.date_range("2000-01-31", "2024-12-31", freq="ME")
    labels = reference_labels(idx)
    assert labels.loc["2008-10-31"] == "crisis"
    assert labels.loc["2020-03-31"] == "crisis"
    assert labels.loc["2022-06-30"] == "tightening"
    assert labels.loc["2013-05-31"] == "expansion"
    assert set(labels.unique()) == {"expansion", "tightening", "crisis"}


def test_confusion_matrix_counts_months():
    idx = pd.date_range("2020-01-31", periods=4, freq="ME")
    labels = pd.Series(["expansion", "crisis", "crisis", "expansion"], index=idx)
    pred = pd.Series(["expansion", "crisis", "expansion", "expansion"], index=idx)
    cm = confusion_matrix(labels, pred)
    assert cm.loc["crisis", "crisis"] == 1
    assert cm.loc["crisis", "expansion"] == 1
    assert cm.loc["expansion", "expansion"] == 2
    assert cm.to_numpy().sum() == 4
    assert accuracy(labels, pred) == 0.75


def test_detection_lag():
    idx = pd.date_range("2020-01-31", periods=6, freq="ME")
    probs = pd.Series([0.1, 0.2, 0.4, 0.8, 0.9, 0.3], index=idx)
    assert detection_lag_months(probs, "2020-02") == 2  # Feb start, crosses in Apr
    assert detection_lag_months(probs, "2020-06") is None
