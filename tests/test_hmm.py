"""HMM invariants (PRD R5/R6): valid distributions, stochastic transition
matrix, determinism, and regime recovery on synthetic data with known truth."""

import numpy as np
import pandas as pd

from atlas.domain.engines.impairment.hmm import fit_hmm, regime_path, regime_probabilities_hmm
from atlas.domain.engines.impairment.regimes import REGIMES, REQUIRED_SERIES


def synthetic_regime_macro(seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    """200 months alternating expansion -> tightening -> crisis with distinct
    macro signatures. Unemployment and the credit spread are built as level
    paths whose CHANGES are the crisis signal (mirrors the production feature
    set: unemployment 12m change, spread 6m change). Returns (frame, labels)."""
    rng = np.random.default_rng(seed)
    blocks = [
        # (label, months, level means, unemp slope/mo, spread slope/mo)
        ("expansion", 60, {"fed_funds": 1.5, "t10y2y": 1.5, "cpi_yoy": 2.0}, 0.0, 0.0),
        ("tightening", 40, {"fed_funds": 5.0, "t10y2y": -0.3, "cpi_yoy": 6.0}, 0.0, 0.0),
        ("crisis", 30, {"fed_funds": 1.0, "t10y2y": 1.0, "cpi_yoy": 0.5}, 0.25, 0.30),
        ("expansion", 70, {"fed_funds": 2.0, "t10y2y": 1.2, "cpi_yoy": 2.5}, -0.05, -0.06),
    ]
    rows, labels = [], []
    unemployment, spread = 4.0, 0.9
    for label, n, means, unemp_slope, spread_slope in blocks:
        for _ in range(n):
            unemployment = max(2.5, unemployment + unemp_slope + rng.normal(0, 0.05))
            spread = max(0.3, spread + spread_slope + rng.normal(0, 0.03))
            row = {k: means[k] + rng.normal(0, 0.15) for k in means}
            row["unemployment"] = unemployment
            row["baa_aaa_spread"] = spread
            rows.append(row)
            labels.append(label)
    idx = pd.date_range("2000-01-31", periods=len(rows), freq="ME")
    frame = pd.DataFrame(rows, index=idx)[list(REQUIRED_SERIES)]
    return frame, pd.Series(labels, index=idx)


def test_transition_matrix_rows_sum_to_one():
    macro, _ = synthetic_regime_macro()
    fit = fit_hmm(macro)
    np.testing.assert_allclose(fit.transition.sum(axis=1), 1.0, atol=1e-10)
    assert (fit.transition >= 0).all()


def test_regime_path_is_valid_distribution():
    macro, _ = synthetic_regime_macro()
    fit = fit_hmm(macro)
    for smoothed in (True, False):
        path = regime_path(macro, fit, smoothed=smoothed)
        assert list(path.columns) == list(REGIMES)
        assert (path.to_numpy() >= 0).all()
        np.testing.assert_allclose(path.sum(axis=1), 1.0, atol=1e-9)


def test_recovers_known_regimes():
    macro, truth = synthetic_regime_macro()
    fit = fit_hmm(macro)
    predicted = regime_path(macro, fit, smoothed=True).idxmax(axis=1)
    # the 12m unemployment-change feature blurs ~12 months at block borders
    aligned = truth.loc[predicted.index]
    assert (predicted == aligned).mean() > 0.75


def test_fit_is_deterministic():
    macro, _ = synthetic_regime_macro()
    f1, f2 = fit_hmm(macro), fit_hmm(macro)
    np.testing.assert_array_equal(f1.means, f2.means)
    np.testing.assert_array_equal(f1.transition, f2.transition)
    assert f1.state_order == f2.state_order


def test_latest_probabilities_interface():
    macro, _ = synthetic_regime_macro()
    probs = regime_probabilities_hmm(macro)
    assert list(probs.index) == list(REGIMES)
    assert np.isclose(probs.sum(), 1.0)
