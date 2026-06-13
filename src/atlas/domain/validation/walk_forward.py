"""Expanding-window crisis validation with no test-period fitting."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from atlas.domain.engines.impairment.hmm import fit_hmm, regime_path
from atlas.domain.engines.impairment.regimes import REQUIRED_SERIES
from atlas.domain.validation.classifier import fit_logistic_crisis_model
from atlas.domain.validation.features import apply_publication_lags, build_crisis_features
from atlas.domain.validation.metrics import binary_metrics, select_threshold


@dataclass(frozen=True)
class WalkForwardFold:
    name: str
    train_end: str
    test_start: str
    test_end: str


DEFAULT_FOLDS = (
    WalkForwardFold("dotcom", "2000-12", "2001-01", "2003-12"),
    WalkForwardFold("gfc", "2006-12", "2007-01", "2010-12"),
    WalkForwardFold("euro_stress", "2010-12", "2011-01", "2013-12"),
    WalkForwardFold("covid", "2019-12", "2020-01", "2022-12"),
    WalkForwardFold("recent", "2022-12", "2023-01", "2026-12"),
)


@dataclass
class WalkForwardResult:
    predictions: pd.DataFrame
    fold_metrics: pd.DataFrame
    aggregate_metrics: pd.DataFrame
    coefficients: pd.DataFrame


def _hmm_features(
    macro: pd.DataFrame,
    train_end: str,
    test_end: str,
) -> pd.DataFrame:
    lagged = apply_publication_lags(macro)
    history = lagged.loc[:test_end, list(REQUIRED_SERIES)].dropna()
    training = history.loc[:train_end]
    fit = fit_hmm(training)
    path = regime_path(history, fit, smoothed=False)
    return path.add_prefix("hmm_")


def run_walk_forward(
    macro: pd.DataFrame,
    labels: pd.Series,
    folds: tuple[WalkForwardFold, ...] = DEFAULT_FOLDS,
    min_recall: float = 0.60,
    include_hmm: bool = True,
) -> WalkForwardResult:
    base_features = build_crisis_features(macro)
    prediction_frames: list[pd.DataFrame] = []
    metric_rows: list[dict[str, float | str]] = []
    coefficient_rows: list[pd.Series] = []

    for fold in folds:
        features = base_features.copy()
        if include_hmm:
            features = features.join(_hmm_features(macro, fold.train_end, fold.test_end))

        dataset = features.join(labels.rename("target"), how="inner").dropna()
        train = dataset.loc[:fold.train_end]
        test = dataset.loc[fold.test_start:fold.test_end]
        if train.empty or test.empty:
            continue

        feature_columns = [column for column in dataset.columns if column != "target"]
        model = fit_logistic_crisis_model(train[feature_columns], train["target"])
        train_probability = model.predict_proba(train[feature_columns])
        threshold = select_threshold(train["target"], train_probability, min_recall=min_recall)
        test_probability = model.predict_proba(test[feature_columns])
        test_prediction = (test_probability >= threshold).astype(int)

        frame = pd.DataFrame(
            {
                "target": test["target"].astype(int),
                "logistic_probability": test_probability,
                "logistic_prediction": test_prediction,
                "fold": fold.name,
                "logistic_threshold": threshold,
            },
            index=test.index,
        )

        if include_hmm:
            hmm_train_probability = train["hmm_crisis"]
            hmm_threshold = select_threshold(
                train["target"], hmm_train_probability, min_recall=min_recall
            )
            frame["hmm_probability"] = test["hmm_crisis"]
            frame["hmm_prediction"] = (frame["hmm_probability"] >= hmm_threshold).astype(int)
            frame["hmm_threshold"] = hmm_threshold

        frame["vix_prediction"] = (
            (macro.loc[frame.index, "vix"] > 30).astype(int) if "vix" in macro else 0
        )
        frame["spread_prediction"] = (
            macro.loc[frame.index, "baa_aaa_spread"].gt(1.2).astype(int)
        )
        prediction_frames.append(frame)

        fold_result = binary_metrics(
            frame["target"], frame["logistic_prediction"], frame["logistic_probability"]
        )
        metric_rows.append({"fold": fold.name, "model": "logistic", **fold_result})
        coefficients = model.coefficient_series()
        coefficients.name = fold.name
        coefficient_rows.append(coefficients)

    if not prediction_frames:
        raise ValueError("walk-forward produced no evaluable folds")

    predictions = pd.concat(prediction_frames).sort_index()
    comparisons = {
        "logistic": ("logistic_prediction", "logistic_probability"),
        "hmm": ("hmm_prediction", "hmm_probability"),
        "vix_rule": ("vix_prediction", "vix_prediction"),
        "spread_rule": ("spread_prediction", "spread_prediction"),
    }
    aggregate_rows = []
    for model_name, (prediction_column, probability_column) in comparisons.items():
        if prediction_column not in predictions:
            continue
        aggregate_rows.append(
            {
                "model": model_name,
                **binary_metrics(
                    predictions["target"],
                    predictions[prediction_column],
                    predictions[probability_column],
                ),
            }
        )

    return WalkForwardResult(
        predictions=predictions,
        fold_metrics=pd.DataFrame(metric_rows).set_index(["fold", "model"]),
        aggregate_metrics=pd.DataFrame(aggregate_rows).set_index("model"),
        coefficients=pd.DataFrame(coefficient_rows),
    )
