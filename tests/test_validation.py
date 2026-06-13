import pandas as pd
import pytest

from atlas.domain.validation.labels import binary_crisis_labels, reference_labels
from atlas.domain.validation.metrics import (
    accuracy,
    average_precision,
    binary_metrics,
    confusion_matrix,
    detection_lag_months,
    select_threshold,
)


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


def test_binary_label_definitions_are_explicit():
    idx = pd.date_range("2011-01-31", "2011-12-31", freq="ME")
    strict = binary_crisis_labels(idx, definition="strict")
    stress = binary_crisis_labels(idx, definition="stress")
    assert strict.sum() == 0
    assert stress.loc["2011-08-31":"2011-12-31"].eq(1).all()


def test_binary_label_horizon_cannot_be_negative():
    idx = pd.date_range("2020-01-31", periods=3, freq="ME")
    with pytest.raises(ValueError, match="horizon_months"):
        binary_crisis_labels(idx, horizon_months=-1)


def test_binary_metrics_and_threshold_selection():
    idx = pd.date_range("2020-01-31", periods=6, freq="ME")
    labels = pd.Series([0, 0, 1, 1, 0, 1], index=idx)
    probabilities = pd.Series([0.1, 0.2, 0.8, 0.7, 0.6, 0.9], index=idx)
    threshold = select_threshold(labels, probabilities, min_recall=2 / 3)
    predictions = (probabilities >= threshold).astype(int)
    metrics = binary_metrics(labels, predictions, probabilities)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["false_alerts_per_year"] == 0.0
    assert average_precision(labels, probabilities) == 1.0
