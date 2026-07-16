"""Company-level EBITDA volatility and dependence calibration."""

from __future__ import annotations

import numpy as np
import pandas as pd

from atlas.domain.engines.impairment.models import CompanyFinancialProfile


def estimate_ebitda_correlation(
    companies: list[CompanyFinancialProfile],
    *,
    shrinkage: float = 0.25,
) -> np.ndarray | None:
    """Estimate a stable correlation matrix from aligned annual EBITDA growth.

    At least four common growth observations are required. Shrinkage toward the
    identity and a PSD projection keep small private-company samples usable.
    """
    if len(companies) < 2 or any(len(company.ebitda_history) < 5 for company in companies):
        return None
    series = []
    for company in companies:
        values = pd.Series(
            {point.year: point.value for point in company.ebitda_history},
            name=company.name,
            dtype=float,
        ).sort_index()
        series.append(np.log(values).diff().dropna())
    aligned = pd.concat(series, axis=1, join="inner").dropna()
    if len(aligned) < 4:
        return None

    empirical = aligned.corr().to_numpy(dtype=float)
    matrix = (1.0 - shrinkage) * empirical + shrinkage * np.eye(len(companies))
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    matrix = eigenvectors @ np.diag(np.maximum(eigenvalues, 1e-8)) @ eigenvectors.T
    scale = np.sqrt(np.diag(matrix))
    matrix = matrix / np.outer(scale, scale)
    np.fill_diagonal(matrix, 1.0)
    return matrix


def resolved_ebitda_correlation(
    companies: list[CompanyFinancialProfile],
    supplied: list[list[float]] | None,
) -> tuple[np.ndarray | None, str]:
    if supplied is not None:
        return np.asarray(supplied, dtype=float), "user"
    estimated = estimate_ebitda_correlation(companies)
    if estimated is not None:
        return estimated, "company-history"
    return None, "structural-fallback"
