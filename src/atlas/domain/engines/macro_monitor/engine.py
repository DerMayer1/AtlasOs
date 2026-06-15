"""Engine 2 - deterministic macro regime and stress monitor.

The monitor turns one frozen macro snapshot into an auditable current state:
filtered regime probabilities, one-month transition probabilities, indicator
trends, stress breadth, alerts and state-conditioned historical references.
It does not forecast asset prices or manufacture point estimates.
"""

from __future__ import annotations

import io
import json
import math
import uuid
from typing import Any

import numpy as np
import pandas as pd

from atlas.domain.engines.impairment.hmm import fit_hmm, regime_path
from atlas.domain.engines.impairment.regimes import REGIMES, REQUIRED_SERIES
from atlas.domain.engines.macro_monitor.models import MacroMonitorParams
from atlas.platform.contracts.schemas import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatus,
    utcnow,
)
from atlas.platform.contracts.worker import RunContext

_OPTIONAL_SERIES = ("vix",)
_STRESS_ORIENTATION = {
    "fed_funds": 1.0,
    "baa_aaa_spread": 1.0,
    "t10y2y": -1.0,
    "cpi_yoy": 1.0,
    "unemployment": 1.0,
    "vix": 1.0,
}


def _clean_macro(macro: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_SERIES if column not in macro.columns]
    if missing:
        raise ValueError(f"macro table missing required series: {missing}")

    columns = list(REQUIRED_SERIES) + [
        column for column in _OPTIONAL_SERIES if column in macro.columns
    ]
    clean = macro[columns].copy().sort_index()
    clean = clean[~clean.index.duplicated(keep="last")]
    clean[list(REQUIRED_SERIES)] = clean[list(REQUIRED_SERIES)].apply(
        pd.to_numeric, errors="coerce"
    )
    clean = clean.dropna(subset=list(REQUIRED_SERIES))
    if len(clean) < 36:
        raise ValueError("macro table needs at least 36 complete observations")
    return clean.astype(float)


def _z_score(series: pd.Series, value: float) -> float:
    std = float(series.std(ddof=0))
    if not np.isfinite(std) or std == 0:
        return 0.0
    return float((value - float(series.mean())) / std)


def _adverse_percentile(series: pd.Series, value: float, orientation: float) -> float:
    rank = float((series <= value).mean())
    return rank if orientation > 0 else 1.0 - rank


def _status(score: float) -> str:
    if score >= 1.5:
        return "critical"
    if score >= 0.75:
        return "elevated"
    if score <= -0.75:
        return "supportive"
    return "neutral"


def _stress_level(score: float) -> str:
    if score >= 1.5:
        return "severe"
    if score >= 0.75:
        return "elevated"
    if score <= -0.75:
        return "supportive"
    return "balanced"


def _probability_confidence(probabilities: np.ndarray) -> float:
    safe = np.clip(probabilities, 1e-12, 1.0)
    entropy = -float(np.sum(safe * np.log(safe)))
    return float(np.clip(1.0 - entropy / math.log(len(safe)), 0.0, 1.0))


def _period_label(value: Any) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _comparison_values(
    params: MacroMonitorParams,
    ctx: RunContext,
    indicators: list[str],
) -> dict[str, float]:
    if params.comparison_snapshot_id is None:
        return {}
    tables = ctx.snapshots.load(params.comparison_snapshot_id)
    if "macro" not in tables:
        raise ValueError(
            f"comparison snapshot {params.comparison_snapshot_id} has no 'macro' table"
        )
    comparison = _clean_macro(tables["macro"])
    return {
        indicator: float(comparison[indicator].dropna().iloc[-1])
        for indicator in indicators
        if indicator in comparison and not comparison[indicator].dropna().empty
    }


def _indicator_rows(
    macro: pd.DataFrame,
    params: MacroMonitorParams,
    comparison: dict[str, float],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    indicators = [
        column
        for column in (*REQUIRED_SERIES, *_OPTIONAL_SERIES)
        if column in macro.columns and not macro[column].dropna().empty
    ]

    for indicator in indicators:
        series = macro[indicator].dropna()
        current = float(series.iloc[-1])
        orientation = _STRESS_ORIENTATION[indicator]
        changes: dict[int, float] = {}
        for months in (1, params.short_window_months, params.long_window_months):
            changes[months] = (
                current - float(series.iloc[-(months + 1)])
                if len(series) > months
                else 0.0
            )

        change_history = series.diff(params.short_window_months).dropna()
        change_z = _z_score(change_history, changes[params.short_window_months])
        level_z = _z_score(series, current)
        stress_score = orientation * level_z
        stress_change_score = orientation * change_z
        row = {
            "indicator": indicator,
            "current_value": current,
            "change_1m": changes[1],
            "change_short": changes[params.short_window_months],
            "change_long": changes[params.long_window_months],
            "level_z_score": level_z,
            "change_z_score": change_z,
            "stress_score": stress_score,
            "stress_change_score": stress_change_score,
            "adverse_percentile": _adverse_percentile(series, current, orientation),
            "snapshot_delta": current - comparison.get(indicator, current),
            "comparison_available": float(indicator in comparison),
        }
        rows.append(row)

        alert_score = max(stress_score, stress_change_score)
        if (
            stress_score >= params.alert_z_threshold
            or stress_change_score >= params.change_z_threshold
        ):
            driver = (
                "adverse level"
                if stress_score >= stress_change_score
                else f"adverse {params.short_window_months}-month change"
            )
            alerts.append(
                {
                    "indicator": indicator,
                    "severity": _status(alert_score),
                    "score": float(alert_score),
                    "level_score": float(stress_score),
                    "change_score": float(stress_change_score),
                    "reason": driver,
                }
            )
    alerts.sort(key=lambda item: item["score"], reverse=True)
    return rows, alerts


def _regime_history(macro: pd.DataFrame):
    fit = fit_hmm(macro)
    path = regime_path(macro, fit, smoothed=False)
    transition = fit.transition[np.ix_(fit.state_order, fit.state_order)]
    latest = path.iloc[-1].to_numpy(dtype=float)
    next_probabilities = latest @ transition
    return fit, path, next_probabilities


def _scenario_rows(
    macro: pd.DataFrame,
    path: pd.DataFrame,
    indicators: list[str],
) -> list[dict[str, Any]]:
    aligned = macro.reindex(path.index)
    assigned = path.idxmax(axis=1)
    rows: list[dict[str, Any]] = []

    base: dict[str, Any] = {"scenario": "base", "sample_size": 1.0}
    for indicator in indicators:
        base[f"{indicator}_level"] = float(macro[indicator].dropna().iloc[-1])
        base[f"{indicator}_delta"] = 0.0
    rows.append(base)

    for regime in ("tightening", "crisis"):
        mask = assigned == regime
        row: dict[str, Any] = {"scenario": regime, "sample_size": float(mask.sum())}
        for indicator in indicators:
            history = aligned.loc[mask, indicator].dropna()
            if history.empty:
                history = macro[indicator].dropna()
            reference = float(history.median())
            current = float(macro[indicator].dropna().iloc[-1])
            row[f"{indicator}_level"] = reference
            row[f"{indicator}_delta"] = reference - current
        rows.append(row)
    return rows


class MacroMonitorEngine:
    name = "macro_monitor"
    engine_version = "1.0.0"
    model_version = "hmm3sc-state-monitor-1.0"

    def describe(self) -> str:
        return (
            "Current macro regime, transition probabilities, indicator trends, "
            "stress breadth, evidence-backed alerts and state-conditioned "
            "historical reference scenarios from a frozen macro snapshot."
        )

    def run(self, request: AnalysisRequest, ctx: RunContext) -> AnalysisResult:
        started = utcnow()
        params = MacroMonitorParams.model_validate(request.params)
        tables = ctx.snapshots.load(request.snapshot_id)
        if "macro" not in tables:
            raise ValueError(f"snapshot {request.snapshot_id} has no 'macro' table")

        macro = _clean_macro(tables["macro"])
        indicators = [
            column
            for column in (*REQUIRED_SERIES, *_OPTIONAL_SERIES)
            if column in macro.columns and not macro[column].dropna().empty
        ]
        comparison = _comparison_values(params, ctx, indicators)
        indicator_rows, alerts = _indicator_rows(macro, params, comparison)
        fit, path, next_probabilities = _regime_history(macro)

        latest = path.iloc[-1]
        previous_index = max(0, len(path) - 1 - params.short_window_months)
        probability_change = latest - path.iloc[previous_index]
        current_regime = str(latest.idxmax())
        confidence = _probability_confidence(latest.to_numpy(dtype=float))

        indicator_frame = pd.DataFrame(indicator_rows)
        stress_index = float(
            np.clip(indicator_frame["stress_score"], -3.0, 3.0).mean()
        )
        stress_breadth = float(
            (indicator_frame["stress_score"] >= 0.75).mean()
        )

        history = path.copy()
        history.insert(0, "period", [_period_label(value) for value in history.index])
        history["confidence"] = [
            _probability_confidence(row)
            for row in path.to_numpy(dtype=float)
        ]
        macro_history = macro[indicators].copy()
        macro_history.insert(
            0,
            "period",
            [_period_label(value) for value in macro_history.index],
        )

        scenario_rows = _scenario_rows(macro, path, indicators)
        regime_probabilities = latest.rename("probability").rename_axis("regime")

        metrics = {
            **{f"p_regime_{regime}": float(latest[regime]) for regime in REGIMES},
            **{
                f"p_next_regime_{regime}": float(next_probabilities[index])
                for index, regime in enumerate(REGIMES)
            },
            "regime_confidence": confidence,
            "stress_index": stress_index,
            "stress_breadth": stress_breadth,
            "n_alerts": float(len(alerts)),
            "n_observations": float(len(macro)),
            "has_vix": float("vix" in indicators),
            "has_comparison_snapshot": float(bool(comparison)),
            **{
                f"stress_{row['indicator']}": float(row["stress_score"])
                for row in indicator_rows
            },
        }

        macro_state = {
            "as_of": _period_label(macro.index[-1]),
            "snapshot_id": request.snapshot_id,
            "comparison_snapshot_id": params.comparison_snapshot_id,
            "regime": {
                "current": current_regime,
                "probabilities": {
                    regime: float(latest[regime]) for regime in REGIMES
                },
                "next_month_probabilities": {
                    regime: float(next_probabilities[index])
                    for index, regime in enumerate(REGIMES)
                },
                "probability_change_short_window": {
                    regime: float(probability_change[regime]) for regime in REGIMES
                },
                "confidence": confidence,
            },
            "stress": {
                "composite": stress_index,
                "breadth": stress_breadth,
                "level": _stress_level(stress_index),
            },
            "indicators": {
                row["indicator"]: {
                    **{
                        key: float(value)
                        for key, value in row.items()
                        if key != "indicator"
                    },
                    "status": _status(float(row["stress_score"])),
                }
                for row in indicator_rows
            },
            "alerts": alerts,
            "scenario_method": "state_conditioned_historical_median",
            "model": {
                "name": self.model_version,
                "log_likelihood": float(fit.log_likelihood),
                "filtered_probabilities": True,
            },
        }

        artifacts = [
            ctx.artifacts.publish(
                ctx.run_id,
                "macro_state.json",
                json.dumps(macro_state, indent=2, sort_keys=True).encode(),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "indicator_snapshot.csv",
                _to_csv(indicator_frame),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "regime_history.csv",
                _to_csv(history.reset_index(drop=True)),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "macro_history.csv",
                _to_csv(macro_history.reset_index(drop=True)),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "scenario_assumptions.csv",
                _to_csv(pd.DataFrame(scenario_rows)),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "regime_probabilities.csv",
                _to_csv(regime_probabilities.reset_index()),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "metrics.json",
                json.dumps(metrics, indent=2, sort_keys=True).encode(),
            ),
        ]

        return AnalysisResult(
            result_id=f"res_{uuid.uuid4().hex[:12]}",
            request_id=request.request_id,
            run_id=ctx.run_id,
            engine=self.name,
            engine_version=self.engine_version,
            model_version=self.model_version,
            snapshot_id=request.snapshot_id,
            status=AnalysisStatus.SUCCEEDED,
            started_at=started,
            finished_at=utcnow(),
            metrics=metrics,
            artifacts=artifacts,
        )


def _to_csv(frame: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    frame.to_csv(
        buffer,
        index=False,
        lineterminator="\n",
        float_format="%.10g",
    )
    return buffer.getvalue().encode()
