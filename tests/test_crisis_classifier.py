import numpy as np
import pandas as pd

from atlas.domain.validation.classifier import fit_logistic_crisis_model
from atlas.domain.validation.features import apply_publication_lags, build_crisis_features
from atlas.domain.validation.walk_forward import (
    MODEL_COLUMNS,
    WalkForwardFold,
    run_walk_forward,
)


def _validation_macro(periods: int = 300) -> tuple[pd.DataFrame, pd.Series]:
    idx = pd.date_range("1990-01-31", periods=periods, freq="ME")
    labels = pd.Series(0, index=idx, dtype=int)
    for start, end in (
        ("1991-01", "1991-06"),
        ("1998-06", "1998-12"),
        ("2003-03", "2003-10"),
        ("2009-01", "2009-08"),
    ):
        labels.loc[start:end] = 1

    cycle = np.sin(np.arange(periods) / 12)
    crisis = labels.to_numpy()
    macro = pd.DataFrame(
        {
            "fed_funds": 3.0 + cycle - 1.5 * crisis,
            "baa_aaa_spread": 0.8 + 1.5 * crisis + 0.1 * cycle,
            "t10y2y": 1.0 - 0.8 * crisis + 0.1 * cycle,
            "cpi_yoy": 2.5 + 0.2 * cycle - 0.5 * crisis,
            "unemployment": 5.0 + 1.2 * crisis - 0.1 * cycle,
            "vix": 18.0 + 25.0 * crisis + cycle,
        },
        index=idx,
    )
    return macro, labels


def test_publication_lags_do_not_expose_current_month_macro_release():
    macro, _ = _validation_macro(periods=24)
    lagged = apply_publication_lags(macro)
    assert lagged.loc[macro.index[1], "cpi_yoy"] == macro.loc[macro.index[0], "cpi_yoy"]
    assert lagged.loc[macro.index[1], "unemployment"] == macro.loc[macro.index[0], "unemployment"]
    assert (
        lagged.loc[macro.index[1], "baa_aaa_spread"] == macro.loc[macro.index[1], "baa_aaa_spread"]
    )


def test_logistic_model_is_deterministic_and_separates_signal():
    macro, labels = _validation_macro()
    features = build_crisis_features(macro).dropna()
    aligned_labels = labels.loc[features.index]
    first = fit_logistic_crisis_model(features, aligned_labels)
    second = fit_logistic_crisis_model(features, aligned_labels)
    np.testing.assert_array_equal(first.coefficients, second.coefficients)
    probabilities = first.predict_proba(features)
    assert probabilities[aligned_labels == 1].mean() > probabilities[aligned_labels == 0].mean()


def test_walk_forward_does_not_use_data_after_fold():
    macro, labels = _validation_macro()
    fold = WalkForwardFold("held_out", "1999-12", "2000-01", "2005-12")
    original = run_walk_forward(macro, labels, folds=(fold,), include_hmm=False)

    changed = macro.copy()
    changed.loc["2006-01":, :] = changed.loc["2006-01":, :] * 100.0
    rerun = run_walk_forward(changed, labels, folds=(fold,), include_hmm=False)

    pd.testing.assert_series_equal(
        original.predictions["logistic_probability"],
        rerun.predictions["logistic_probability"],
    )
    assert original.aggregate_metrics.loc["logistic", "recall"] > 0.0


def test_fold_metrics_cover_every_aggregated_model():
    """Per-fold and aggregate tables must describe the same set of models.

    Regression guard: fold metrics were previously emitted for the logistic
    model only, so a report could publish logistic fold numbers underneath a
    hybrid headline without either table saying so.
    """
    macro, labels = _validation_macro()
    folds = (
        WalkForwardFold("first", "1999-12", "2000-01", "2005-12"),
        WalkForwardFold("second", "2007-12", "2008-01", "2014-12"),
    )

    result = run_walk_forward(macro, labels, folds=folds, include_hmm=False)

    aggregated = set(result.aggregate_metrics.index)
    assert aggregated == {
        name
        for name, (prediction_column, _) in MODEL_COLUMNS.items()
        if prediction_column in result.predictions
    }
    for fold in folds:
        assert set(result.fold_metrics.xs(fold.name, level="fold").index) == aggregated


def test_hybrid_classifier_adds_fixed_vix_recall_without_future_fitting():
    macro, labels = _validation_macro()
    fold = WalkForwardFold("held_out", "2007-12", "2008-01", "2014-12")

    result = run_walk_forward(macro, labels, folds=(fold,), include_hmm=False)

    assert "hybrid_probability" in result.predictions
    assert (
        result.aggregate_metrics.loc["hybrid", "recall"]
        >= result.aggregate_metrics.loc["logistic", "recall"]
    )
    assert (
        result.predictions.loc[macro.loc[result.predictions.index, "vix"] > 30, "hybrid_prediction"]
        .eq(1)
        .all()
    )
