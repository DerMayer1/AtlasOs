"""Deterministic rules that turn engine metrics into a cited decision report.

The thresholds below are policy, not model output: they decide *when* a number
is worth surfacing as an action, but never change the number itself. The action
text always cites the artifact value that triggered it, so the recommendation is
auditable end to end.
"""

from __future__ import annotations

import uuid
from typing import Any

from atlas.domain.reports.models import Action, Citation, Figure, Report, Severity

# --- impairment policy thresholds --------------------------------------------
IMPAIRMENT_REVIEW = 0.15  # mean P(impairment) above which valuation review is due
IMPAIRMENT_ELEVATED = 0.30
CRISIS_LOSS_RATIO_ELEVATED = 0.25  # crisis 1y expected loss ratio worth escalating
LIQUIDITY_GAP_TO_EBITDA = 0.50  # 1y funding gap above half of EBITDA
INTEREST_COVERAGE_FLOOR = 2.0
MATERIAL_INCREASE_ABS = 0.05  # absolute jump in mean P(impairment) vs previous run

# --- macro policy thresholds -------------------------------------------------
STRESS_ELEVATED = 0.50
STRESS_CRITICAL = 0.66
NEXT_CRISIS_WATCH = 0.30

_METRICS = "metrics.json"
_RESILIENCE = "financial_resilience.csv"
_REGIMES = ("expansion", "tightening", "crisis")


def _cite(artifact: str, locator: str) -> Citation:
    return Citation(artifact=artifact, locator=locator)


def _metric_figure(
    metrics: dict[str, float],
    key: str,
    label: str,
    fmt: str,
    severity: Severity = "info",
) -> Figure | None:
    if key not in metrics:
        return None
    return Figure(
        label=label,
        value=float(metrics[key]),
        format=fmt,  # type: ignore[arg-type]
        severity=severity,
        citation=_cite(_METRICS, key),
    )


def build_report(
    *,
    run_id: str,
    engine: str,
    snapshot_id: str,
    engine_version: str,
    model_version: str,
    metrics: dict[str, float],
    resilience_rows: list[dict[str, Any]] | None = None,
    previous_metrics: dict[str, float] | None = None,
    previous_run_id: str | None = None,
) -> Report:
    """Build a decision report from one run's metrics (and optional artifacts).

    ``resilience_rows`` are the parsed rows of ``financial_resilience.csv`` and
    drive the per-company liquidity actions. ``previous_metrics`` enable the
    "material change since last analysis" escalation.
    """

    if engine == "impairment":
        headline, figures, drivers, actions = _impairment(
            metrics, resilience_rows or [], previous_metrics
        )
    elif engine == "macro_monitor":
        headline, figures, drivers, actions = _macro_monitor(metrics)
    else:  # pragma: no cover - guarded by the endpoint
        headline = f"No report template for engine {engine!r}."
        figures, drivers, actions = [], [], []

    return Report(
        report_id=f"rep_{uuid.uuid4().hex[:12]}",
        run_id=run_id,
        engine=engine,
        snapshot_id=snapshot_id,
        engine_version=engine_version,
        model_version=model_version,
        headline=headline,
        key_figures=figures,
        risk_drivers=drivers,
        actions=actions,
        previous_run_id=previous_run_id if previous_metrics else None,
    )


def _severity_for_impairment(value: float) -> Severity:
    if value >= IMPAIRMENT_ELEVATED:
        return "critical"
    if value >= IMPAIRMENT_REVIEW:
        return "elevated"
    return "info"


def _impairment(
    metrics: dict[str, float],
    resilience_rows: list[dict[str, Any]],
    previous: dict[str, float] | None,
) -> tuple[str, list[Figure], list[Figure], list[Action]]:
    mean_p = float(metrics.get("portfolio_mean_p_impairment", 0.0))
    figures = [
        f
        for f in (
            _metric_figure(
                metrics,
                "portfolio_mean_p_impairment",
                "Mean P(impairment)",
                "ratio",
                _severity_for_impairment(mean_p),
            ),
            _metric_figure(
                metrics,
                "portfolio_expected_impairment_loss",
                "Expected impairment loss (base, 1y)",
                "currency",
            ),
            _metric_figure(
                metrics,
                "portfolio_loss_p95",
                "Tail loss (P95, base 1y)",
                "currency",
            ),
            _metric_figure(metrics, "n_companies", "Companies", "count"),
        )
        if f is not None
    ]

    drivers: list[Figure] = []
    crisis = _metric_figure(
        metrics,
        "crisis_1y_expected_loss_ratio",
        "Crisis 1y expected loss ratio",
        "ratio",
        "elevated"
        if metrics.get("crisis_1y_expected_loss_ratio", 0.0) >= CRISIS_LOSS_RATIO_ELEVATED
        else "info",
    )
    if crisis is not None:
        drivers.append(crisis)
    regime_crisis = _metric_figure(
        metrics, "p_regime_crisis", "Current macro P(crisis)", "ratio"
    )
    if regime_crisis is not None:
        drivers.append(regime_crisis)

    actions: list[Action] = []

    # R1 — valuation review when expected impairment is material.
    if mean_p >= IMPAIRMENT_REVIEW:
        actions.append(
            Action(
                code="valuation_review",
                title="Request valuation review",
                severity=_severity_for_impairment(mean_p),
                rationale=(
                    f"Mean P(impairment) is {mean_p:.0%}, above the "
                    f"{IMPAIRMENT_REVIEW:.0%} review threshold."
                ),
                citations=[_cite(_METRICS, "portfolio_mean_p_impairment")],
            )
        )

    # R2 — capital/tail attention when the crisis scenario erodes a lot of value.
    crisis_ratio = float(metrics.get("crisis_1y_expected_loss_ratio", 0.0))
    if crisis_ratio >= CRISIS_LOSS_RATIO_ELEVATED:
        actions.append(
            Action(
                code="stress_capital_review",
                title="Reassess capital against the crisis scenario",
                severity="elevated",
                rationale=(
                    f"A crisis regime erodes {crisis_ratio:.0%} of carrying value "
                    f"within one year (>= {CRISIS_LOSS_RATIO_ELEVATED:.0%})."
                ),
                citations=[_cite(_METRICS, "crisis_1y_expected_loss_ratio")],
            )
        )

    # R3 — per-company refinancing/liquidity from the resilience diagnostics.
    for row in resilience_rows:
        company = str(row.get("company", "?"))
        gap_ratio = _as_float(row.get("liquidity_gap_to_ebitda"))
        coverage = _as_float(row.get("interest_coverage"))
        reasons: list[str] = []
        citations: list[Citation] = []
        if gap_ratio is not None and gap_ratio >= LIQUIDITY_GAP_TO_EBITDA:
            reasons.append(
                f"1y funding gap is {gap_ratio:.2f}x EBITDA "
                f"(>= {LIQUIDITY_GAP_TO_EBITDA:.2f})"
            )
            citations.append(_cite(_RESILIENCE, f"{company}.liquidity_gap_to_ebitda"))
        if coverage is not None and coverage < INTEREST_COVERAGE_FLOOR:
            reasons.append(
                f"interest coverage is {coverage:.1f}x "
                f"(< {INTEREST_COVERAGE_FLOOR:.1f})"
            )
            citations.append(_cite(_RESILIENCE, f"{company}.interest_coverage"))
        if reasons:
            actions.append(
                Action(
                    code="refinancing_review",
                    title=f"Review refinancing for {company}",
                    severity="elevated",
                    rationale=f"{company}: " + "; ".join(reasons) + ".",
                    citations=citations,
                )
            )

    # R4 — escalate a material increase versus the previous analysis.
    if previous is not None and "portfolio_mean_p_impairment" in previous:
        prev_p = float(previous["portfolio_mean_p_impairment"])
        delta = mean_p - prev_p
        if delta >= MATERIAL_INCREASE_ABS:
            actions.append(
                Action(
                    code="escalate_increase",
                    title="Escalate: risk rose since last analysis",
                    severity="elevated",
                    rationale=(
                        f"Mean P(impairment) rose {delta:+.0%} "
                        f"(from {prev_p:.0%} to {mean_p:.0%}) versus the previous run."
                    ),
                    citations=[_cite(_METRICS, "portfolio_mean_p_impairment")],
                )
            )

    headline = (
        f"Portfolio mean P(impairment) is {mean_p:.0%} across "
        f"{int(metrics.get('n_companies', 0))} companies; "
        f"{len(actions)} action(s) flagged."
    )
    return headline, figures, drivers, actions


def _macro_monitor(
    metrics: dict[str, float],
) -> tuple[str, list[Figure], list[Figure], list[Action]]:
    regime = max(_REGIMES, key=lambda name: metrics.get(f"p_regime_{name}", 0.0))
    stress = float(metrics.get("stress_index", 0.0))
    next_crisis = float(metrics.get("p_next_regime_crisis", 0.0))

    figures = [
        f
        for f in (
            _metric_figure(
                metrics,
                f"p_regime_{regime}",
                f"Current regime: {regime}",
                "ratio",
                _macro_severity(stress),
            ),
            _metric_figure(metrics, "stress_index", "Composite stress", "ratio"),
            _metric_figure(metrics, "stress_breadth", "Pressured indicators", "ratio"),
            _metric_figure(metrics, "n_alerts", "Active alerts", "count"),
        )
        if f is not None
    ]
    drivers = [
        f
        for f in (
            _metric_figure(
                metrics, "p_next_regime_crisis", "Next-month P(crisis)", "ratio"
            ),
            _metric_figure(metrics, "regime_confidence", "Regime confidence", "ratio"),
        )
        if f is not None
    ]

    actions: list[Action] = []
    if regime == "crisis" or stress >= STRESS_CRITICAL:
        actions.append(
            Action(
                code="macro_heightened_monitoring",
                title="Move to heightened monitoring",
                severity="critical" if stress >= STRESS_CRITICAL else "elevated",
                rationale=(
                    f"Filtered regime is {regime!r} with composite stress {stress:.2f}."
                ),
                citations=[
                    _cite(_METRICS, f"p_regime_{regime}"),
                    _cite(_METRICS, "stress_index"),
                ],
            )
        )
    elif stress >= STRESS_ELEVATED:
        actions.append(
            Action(
                code="macro_review_exposures",
                title="Review macro-sensitive exposures",
                severity="watch",
                rationale=f"Composite stress {stress:.2f} is in the elevated band.",
                citations=[_cite(_METRICS, "stress_index")],
            )
        )
    if next_crisis >= NEXT_CRISIS_WATCH:
        actions.append(
            Action(
                code="macro_transition_watch",
                title="Watch crisis transition risk",
                severity="watch",
                rationale=(
                    f"Next-month transition into crisis is {next_crisis:.0%} "
                    f"(>= {NEXT_CRISIS_WATCH:.0%})."
                ),
                citations=[_cite(_METRICS, "p_next_regime_crisis")],
            )
        )

    headline = (
        f"Macro regime is {regime} with composite stress {stress:.2f}; "
        f"{len(actions)} action(s) flagged."
    )
    return headline, figures, drivers, actions


def _macro_severity(stress: float) -> Severity:
    if stress >= STRESS_CRITICAL:
        return "critical"
    if stress >= STRESS_ELEVATED:
        return "elevated"
    return "info"


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
