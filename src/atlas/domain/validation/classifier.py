"""Small deterministic regularized logistic classifier.

The implementation stays in NumPy so validation remains reproducible without a
second modelling stack. Balanced sample weights help the rare crisis class;
the fitted intercept is then corrected back to the observed training
prevalence so returned probabilities retain a meaningful base rate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def _sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-values))


@dataclass(frozen=True)
class LogisticCrisisModel:
    columns: tuple[str, ...]
    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray
    intercept: float

    def predict_proba(self, features: pd.DataFrame) -> pd.Series:
        missing = sorted(set(self.columns).difference(features.columns))
        if missing:
            raise ValueError(f"features missing model columns: {missing}")
        x = features.loc[:, self.columns].to_numpy(dtype=float)
        if not np.isfinite(x).all():
            raise ValueError("features contain NaN or infinite values")
        z = (x - self.mean) / self.scale
        probabilities = _sigmoid(z @ self.coefficients + self.intercept)
        return pd.Series(probabilities, index=features.index, name="crisis_probability")

    def coefficient_series(self) -> pd.Series:
        return pd.Series(self.coefficients, index=list(self.columns), name="coefficient")


def fit_logistic_crisis_model(
    features: pd.DataFrame,
    labels: pd.Series,
    l2: float = 1.0,
    max_iter: int = 100,
    tol: float = 1e-8,
) -> LogisticCrisisModel:
    """Fit a class-balanced L2 logistic model with deterministic Newton steps."""
    aligned = features.join(labels.rename("target"), how="inner").dropna()
    if aligned.empty:
        raise ValueError("no aligned observations available for logistic fit")
    x = aligned[features.columns].to_numpy(dtype=float)
    y = aligned["target"].to_numpy(dtype=float)
    if set(np.unique(y)) != {0.0, 1.0}:
        raise ValueError("logistic training requires both crisis and non-crisis observations")

    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale == 0.0] = 1.0
    z = (x - mean) / scale
    design = np.column_stack([np.ones(len(z)), z])

    prevalence = float(y.mean())
    class_weights = np.where(y == 1.0, 0.5 / prevalence, 0.5 / (1.0 - prevalence))
    beta = np.zeros(design.shape[1])
    penalty = np.diag(np.r_[0.0, np.full(design.shape[1] - 1, l2)])

    for _ in range(max_iter):
        probabilities = _sigmoid(design @ beta)
        variance = np.maximum(probabilities * (1.0 - probabilities), 1e-8)
        gradient = design.T @ (class_weights * (probabilities - y)) + penalty @ beta
        hessian = (
            design.T @ (design * (class_weights * variance)[:, None])
            + penalty
            + np.eye(design.shape[1]) * 1e-9
        )
        step = np.linalg.solve(hessian, gradient)
        beta -= step
        if np.max(np.abs(step)) < tol:
            break

    # Balanced fitting assumes a 50/50 prior. Restore the observed base rate.
    beta[0] += np.log(prevalence / (1.0 - prevalence))
    return LogisticCrisisModel(
        columns=tuple(features.columns),
        mean=mean,
        scale=scale,
        coefficients=beta[1:],
        intercept=float(beta[0]),
    )
