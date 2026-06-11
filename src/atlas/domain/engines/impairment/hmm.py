"""Gaussian HMM for macro regime classification (PRD R6 model, Phase 2).

Three hidden states over the z-scored macro series, diagonal covariance,
fitted by EM (Baum-Welch) with scaled forward-backward. Written in plain
numpy on purpose: ~150 lines we fully control beats an opaque dependency
when every number must be reproducible (seeded k-means init + fixed
iteration budget => same data, same fit, bit for bit).

State labels are assigned post-fit from state means:
  crisis     = state with highest credit-spread + unemployment loading
  tightening = of the rest, state with highest fed-funds + CPI loading
  expansion  = the remaining state
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from atlas.domain.engines.impairment.regimes import REGIMES, REQUIRED_SERIES

_K = 3
_MIN_VAR = 1e-3
_SEED = 1234

# Model features. Unemployment enters as its 12-month change, not its level:
# the level is a lagging indicator that stays elevated for years after a
# recession ends (2009-2015), which made the crisis state absorb the recovery
# (first validation run: 124 expansion months predicted as crisis).
FEATURES = ("fed_funds", "baa_aaa_spread", "t10y2y", "cpi_yoy", "unemployment_chg12")


def build_features(macro: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_SERIES if c not in macro.columns]
    if missing:
        raise ValueError(f"macro table missing required series: {missing}")
    feats = macro[["fed_funds", "baa_aaa_spread", "t10y2y", "cpi_yoy"]].copy()
    feats["unemployment_chg12"] = macro["unemployment"].diff(12)
    return feats.dropna()


@dataclass(frozen=True)
class HMMFit:
    means: np.ndarray  # (K, D) in z-space
    variances: np.ndarray  # (K, D)
    transition: np.ndarray  # (K, K), rows sum to 1
    initial: np.ndarray  # (K,)
    state_order: tuple[int, ...]  # state index per REGIMES position
    feature_mean: np.ndarray  # (D,) standardization params
    feature_std: np.ndarray  # (D,)
    log_likelihood: float


def _standardize(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = values.mean(axis=0)
    std = values.std(axis=0)
    std[std == 0] = 1.0
    return (values - mean) / std, mean, std


def _kmeans_init(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Deterministic k-means; returns (K, D) centers."""
    centers = x[rng.choice(len(x), size=_K, replace=False)]
    for _ in range(50):
        dists = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = dists.argmin(axis=1)
        new = np.array(
            [x[labels == k].mean(axis=0) if (labels == k).any() else centers[k] for k in range(_K)]
        )
        if np.allclose(new, centers):
            break
        centers = new
    return centers


def _log_gauss(x: np.ndarray, means: np.ndarray, variances: np.ndarray) -> np.ndarray:
    """(T, K) log densities under diagonal Gaussians."""
    t, d = x.shape
    out = np.empty((t, _K))
    for k in range(_K):
        diff2 = (x - means[k]) ** 2 / variances[k]
        out[:, k] = -0.5 * (d * np.log(2 * np.pi) + np.log(variances[k]).sum() + diff2.sum(axis=1))
    return out


def _forward_backward(
    log_b: np.ndarray, transition: np.ndarray, initial: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Scaled forward-backward. Returns (alpha, beta, scale, loglik)."""
    t_len = len(log_b)
    b = np.exp(log_b - log_b.max(axis=1, keepdims=True))
    alpha = np.empty((t_len, _K))
    beta = np.ones((t_len, _K))
    scale = np.empty(t_len)

    def _normalize(vec: np.ndarray) -> tuple[np.ndarray, float]:
        s = vec.sum()
        if not np.isfinite(s) or s <= 0.0:
            # All paths died numerically (observation far outside every state,
            # e.g. out-of-sample shocks). Reset to uniform instead of NaN-ing
            # the rest of the path; the next informative observation re-anchors.
            return np.full(_K, 1.0 / _K), 1.0
        return vec / s, float(s)

    alpha[0], scale[0] = _normalize(initial * b[0])
    for t in range(1, t_len):
        alpha[t], scale[t] = _normalize((alpha[t - 1] @ transition) * b[t])

    # Per-step renormalization of beta is safe: gamma and xi are normalized
    # row-wise downstream, so any positive per-t scaling of beta cancels out.
    for t in range(t_len - 2, -1, -1):
        beta[t], _ = _normalize(transition @ (b[t + 1] * beta[t + 1]))

    loglik = float(np.log(scale).sum() + log_b.max(axis=1).sum())
    return alpha, beta, scale, loglik


def fit_hmm(macro: pd.DataFrame, max_iter: int = 200, tol: float = 1e-6) -> HMMFit:
    values = build_features(macro).to_numpy(dtype=float)
    if len(values) < 24:
        raise ValueError("not enough observations after feature construction (need >= 24)")
    if np.isnan(values).any():
        raise ValueError("macro frame contains NaNs; ingestion must fail loudly upstream")
    x, feat_mean, feat_std = _standardize(values)

    rng = np.random.default_rng(_SEED)
    means = _kmeans_init(x, rng)
    variances = np.ones((_K, x.shape[1]))
    transition = np.full((_K, _K), 0.1 / (_K - 1)) + np.eye(_K) * (0.9 - 0.1 / (_K - 1))
    transition /= transition.sum(axis=1, keepdims=True)
    initial = np.full(_K, 1.0 / _K)

    prev_ll = -np.inf
    for _ in range(max_iter):
        log_b = _log_gauss(x, means, variances)
        alpha, beta, scale, ll = _forward_backward(log_b, transition, initial)

        gamma = alpha * beta
        gamma /= gamma.sum(axis=1, keepdims=True)

        b = np.exp(log_b - log_b.max(axis=1, keepdims=True))
        xi_sum = np.zeros((_K, _K))
        for t in range(len(x) - 1):
            xi = (alpha[t][:, None] * transition) * (b[t + 1] * beta[t + 1])[None, :]
            xi_sum += xi / xi.sum()

        initial = gamma[0]
        transition = xi_sum / xi_sum.sum(axis=1, keepdims=True)
        weights = gamma.sum(axis=0)
        means = (gamma.T @ x) / weights[:, None]
        for k in range(_K):
            diff = x - means[k]
            variances[k] = np.maximum((gamma[:, k][:, None] * diff**2).sum(0) / weights[k],
                                      _MIN_VAR)

        if abs(ll - prev_ll) < tol:
            break
        prev_ll = ll

    state_order = _label_states(means)
    return HMMFit(
        means=means,
        variances=variances,
        transition=transition,
        initial=initial,
        state_order=state_order,
        feature_mean=feat_mean,
        feature_std=feat_std,
        log_likelihood=prev_ll,
    )


def _label_states(means: np.ndarray) -> tuple[int, ...]:
    """Map raw state indices to (expansion, tightening, crisis) positions."""
    spread_i = FEATURES.index("baa_aaa_spread")
    unemp_i = FEATURES.index("unemployment_chg12")
    ff_i = FEATURES.index("fed_funds")
    cpi_i = FEATURES.index("cpi_yoy")

    crisis = int(np.argmax(means[:, spread_i] + means[:, unemp_i]))
    rest = [k for k in range(_K) if k != crisis]
    tightening = max(rest, key=lambda k: means[k, ff_i] + means[k, cpi_i])
    expansion = next(k for k in rest if k != tightening)
    return (expansion, tightening, crisis)


def regime_path(macro: pd.DataFrame, fit: HMMFit, smoothed: bool = True) -> pd.DataFrame:
    """Per-period regime probabilities for `macro` under `fit`.

    smoothed=True uses all data (validation); False uses filtered (causal)
    probabilities — what was knowable at each point in time.
    """
    feats = build_features(macro)
    x = (feats.to_numpy(dtype=float) - fit.feature_mean) / fit.feature_std
    log_b = _log_gauss(x, fit.means, fit.variances)
    alpha, beta, _, _ = _forward_backward(log_b, fit.transition, fit.initial)
    probs = alpha * beta if smoothed else alpha
    probs = probs / probs.sum(axis=1, keepdims=True)
    return pd.DataFrame(probs[:, list(fit.state_order)], index=feats.index, columns=list(REGIMES))


def regime_probabilities_hmm(macro: pd.DataFrame) -> pd.Series:
    """Fit on full history, return filtered probabilities of the latest period.

    Drop-in replacement for regimes.regime_probabilities (ADR-002 fulfilled).
    """
    if len(macro) < 36:
        raise ValueError("macro table needs at least 36 observations to fit the HMM")
    fit = fit_hmm(macro)
    path = regime_path(macro, fit, smoothed=False)
    latest = path.iloc[-1]
    latest.name = "probability"
    return latest
