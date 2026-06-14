"""Engine 1 - joint portfolio impairment analysis.

The model separates four concerns:
1. macro regime probabilities from the frozen snapshot;
2. correlated EBITDA paths with market, sector and company factors;
3. stochastic valuation multiples with regime compression;
4. accounting impairment and financial-resilience diagnostics.

The same random factor draws are reused across scenarios and horizons. This
makes comparisons controlled and keeps the run deterministic for a fixed seed.
"""

from __future__ import annotations

import io
import json
import math
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from atlas.domain.engines.impairment.hmm import regime_probabilities_hmm
from atlas.domain.engines.impairment.models import (
    CompanyFinancialProfile,
    ImpairmentParams,
    ScenarioName,
)
from atlas.domain.engines.impairment.regimes import REGIMES, regime_probabilities
from atlas.platform.contracts.schemas import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatus,
    utcnow,
)
from atlas.platform.contracts.worker import RunContext

_CALIBRATION_FILE = Path(__file__).parent / "shock_calibration.json"
_FALLBACK_SHOCKS = {
    "expansion": (0.05, 0.08),
    "tightening": (-0.02, 0.12),
    "crisis": (-0.15, 0.20),
}
_MULTIPLE_COMPRESSION = {
    "expansion": 0.04,
    "tightening": -0.12,
    "crisis": -0.30,
}


def _load_shocks() -> dict[str, tuple[float, float]]:
    if _CALIBRATION_FILE.exists():
        data = json.loads(_CALIBRATION_FILE.read_text())
        return {r: (v["mean"], v["std"]) for r, v in data["shocks"].items()}
    return dict(_FALLBACK_SHOCKS)


_SHOCKS = _load_shocks()
_SHOCK_MEANS = np.array([_SHOCKS[regime][0] for regime in REGIMES])
_SHOCK_STDS = np.array([_SHOCKS[regime][1] for regime in REGIMES])
_MULTIPLE_COMPRESSIONS = np.array(
    [_MULTIPLE_COMPRESSION[regime] for regime in REGIMES]
)


@dataclass(frozen=True)
class FactorDraws:
    market: np.ndarray
    sectors: dict[str, np.ndarray]
    company: np.ndarray
    multiple: np.ndarray
    base_regimes: np.ndarray


@dataclass(frozen=True)
class CompanySimulation:
    ebitda: np.ndarray
    multiple: np.ndarray
    recoverable_amount: np.ndarray
    impairment_loss: np.ndarray


def _lognormal_parameters(arithmetic_mean: np.ndarray, arithmetic_std: np.ndarray):
    """Convert arithmetic growth moments into positive gross-factor moments."""
    gross_mean = np.maximum(1.0 + arithmetic_mean, 0.05)
    variance_ratio = np.square(arithmetic_std / gross_mean)
    sigma_log = np.sqrt(np.log1p(variance_ratio))
    mu_log = np.log(gross_mean) - 0.5 * np.square(sigma_log)
    return mu_log, sigma_log


def _regime_draws(
    scenario: ScenarioName,
    base_regimes: np.ndarray,
    n_sims: int,
) -> np.ndarray:
    if scenario == "base":
        return base_regimes
    return np.full(n_sims, REGIMES.index(scenario), dtype=int)


def _factor_for_company(
    company: CompanyFinancialProfile,
    index: int,
    draws: FactorDraws,
    params: ImpairmentParams,
) -> np.ndarray:
    market_share = params.market_variance_share
    sector_share = params.sector_variance_share
    idiosyncratic_share = 1.0 - market_share - sector_share

    market_weight = math.sqrt(market_share) * company.macro_sensitivity
    sector_weight = math.sqrt(sector_share) * company.sector_sensitivity
    idiosyncratic_weight = math.sqrt(idiosyncratic_share)
    scale = math.sqrt(
        market_weight**2 + sector_weight**2 + idiosyncratic_weight**2
    )
    return (
        market_weight * draws.market
        + sector_weight * draws.sectors[company.sector]
        + idiosyncratic_weight * draws.company[index]
    ) / scale


def _simulate_company(
    company: CompanyFinancialProfile,
    company_index: int,
    regimes: np.ndarray,
    horizon: int,
    draws: FactorDraws,
    params: ImpairmentParams,
) -> CompanySimulation:
    means = _SHOCK_MEANS[regimes]
    calibrated_stds = _SHOCK_STDS[regimes]
    means = means * company.macro_sensitivity
    annual_stds = np.maximum(
        company.ebitda_volatility,
        calibrated_stds * max(company.macro_sensitivity, 0.5),
    )

    company_factor = _factor_for_company(company, company_index, draws, params)
    mu_log, sigma_log = _lognormal_parameters(means, annual_stds)
    ebitda = company.ebitda * np.exp(
        mu_log * horizon + sigma_log * math.sqrt(horizon) * company_factor
    )

    compression = _MULTIPLE_COMPRESSIONS[regimes]
    target_multiple = company.multiple * (1.0 + compression)
    target_multiple = np.clip(
        target_multiple,
        company.resolved_multiple_floor,
        company.resolved_multiple_ceiling,
    )
    correlation = params.multiple_ebitda_correlation
    multiple_factor = (
        correlation * company_factor
        + math.sqrt(1.0 - correlation**2) * draws.multiple[company_index]
    )
    multiple_sigma = company.multiple_volatility * math.sqrt(horizon)
    multiple = target_multiple * np.exp(
        -0.5 * multiple_sigma**2 + multiple_sigma * multiple_factor
    )
    multiple = np.clip(
        multiple,
        company.resolved_multiple_floor,
        company.resolved_multiple_ceiling,
    )

    recoverable_amount = ebitda * multiple
    impairment_loss = np.maximum(company.carrying_value - recoverable_amount, 0.0)
    return CompanySimulation(
        ebitda=ebitda,
        multiple=multiple,
        recoverable_amount=recoverable_amount,
        impairment_loss=impairment_loss,
    )


def _company_row(
    company: CompanyFinancialProfile,
    simulation: CompanySimulation,
) -> dict[str, float]:
    impaired = simulation.impairment_loss > 0
    return {
        "p_impairment": float(np.mean(impaired)),
        "expected_impairment_loss": float(simulation.impairment_loss.mean()),
        "expected_loss_ratio": float(
            simulation.impairment_loss.mean() / company.carrying_value
        ),
        "recoverable_mean": float(simulation.recoverable_amount.mean()),
        "recoverable_p05": float(np.percentile(simulation.recoverable_amount, 5)),
        "recoverable_p95": float(np.percentile(simulation.recoverable_amount, 95)),
        "ebitda_mean": float(simulation.ebitda.mean()),
        "multiple_mean": float(simulation.multiple.mean()),
        "carrying_value": company.carrying_value,
    }


def _portfolio_row(
    simulations: list[CompanySimulation],
    companies: list[CompanyFinancialProfile],
) -> dict[str, float]:
    losses = np.vstack([sim.impairment_loss for sim in simulations])
    portfolio_loss = losses.sum(axis=0)
    total_carrying = sum(company.carrying_value for company in companies)
    weighted_prob = sum(
        np.mean(sim.impairment_loss > 0) * company.carrying_value
        for sim, company in zip(simulations, companies, strict=True)
    ) / total_carrying
    return {
        "p_any_impairment": float(np.mean(portfolio_loss > 0)),
        "carrying_weighted_p_impairment": float(weighted_prob),
        "expected_impairment_loss": float(portfolio_loss.mean()),
        "expected_loss_ratio": float(portfolio_loss.mean() / total_carrying),
        "loss_p50": float(np.percentile(portfolio_loss, 50)),
        "loss_p95": float(np.percentile(portfolio_loss, 95)),
        "loss_p99": float(np.percentile(portfolio_loss, 99)),
        "total_carrying_value": float(total_carrying),
    }


def _sensitivity_rows(
    companies: list[CompanyFinancialProfile],
    simulations: list[CompanySimulation],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for company, simulation in zip(companies, simulations, strict=True):
        base_p = float(np.mean(simulation.recoverable_amount < company.carrying_value))
        downside_p = float(
            np.mean(simulation.recoverable_amount * 0.9 < company.carrying_value)
        )
        carrying_up_p = float(
            np.mean(simulation.recoverable_amount < company.carrying_value * 1.1)
        )
        rows.append(
            {
                "company": company.name,
                "p_impairment_base": base_p,
                "delta_p_ebitda_down_10": downside_p - base_p,
                "delta_p_multiple_down_10": downside_p - base_p,
                "delta_p_carrying_up_10": carrying_up_p - base_p,
                "break_even_ebitda": company.carrying_value / company.multiple,
                "break_even_multiple": company.carrying_value / company.ebitda,
                "current_valuation_headroom": (
                    company.ebitda * company.multiple - company.carrying_value
                ),
            }
        )
    return rows


def _resilience_rows(
    companies: list[CompanyFinancialProfile],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for company in companies:
        interest_expense = company.resolved_interest_expense
        net_debt = company.debt - company.cash
        liquidity_gap = max(company.debt_due_1y - company.cash, 0.0)
        rows.append(
            {
                "company": company.name,
                "net_debt": net_debt,
                "net_leverage": net_debt / company.ebitda,
                "annual_interest_expense": interest_expense,
                "interest_coverage": (
                    company.ebitda / interest_expense
                    if interest_expense > 0
                    else 999.0
                ),
                "debt_due_1y": company.debt_due_1y,
                "liquidity_gap_1y": liquidity_gap,
                "liquidity_gap_to_ebitda": liquidity_gap / company.ebitda,
            }
        )
    return rows


class ImpairmentEngine:
    name = "impairment"
    engine_version = "1.0.0"
    model_version = "hmm3sc-joint-factor-1.0"

    def describe(self) -> str:
        return (
            "Joint portfolio impairment analysis with correlated macro, sector and "
            "company EBITDA factors, stochastic multiples, scenarios, expected "
            "losses, sensitivities and separate financial-resilience diagnostics."
        )

    def run(self, request: AnalysisRequest, ctx: RunContext) -> AnalysisResult:
        started = utcnow()
        params = ImpairmentParams.model_validate(request.params)
        tables = ctx.snapshots.load(request.snapshot_id)
        if "macro" not in tables:
            raise ValueError(f"snapshot {request.snapshot_id} has no 'macro' table")

        regime_probs = (
            regime_probabilities_hmm(tables["macro"])
            if params.regime_model == "hmm"
            else regime_probabilities(tables["macro"])
        )
        rng = np.random.default_rng(params.seed)
        sectors = sorted({company.sector for company in params.companies})
        draws = FactorDraws(
            market=rng.standard_normal(params.n_sims),
            sectors={sector: rng.standard_normal(params.n_sims) for sector in sectors},
            company=rng.standard_normal((len(params.companies), params.n_sims)),
            multiple=rng.standard_normal((len(params.companies), params.n_sims)),
            base_regimes=rng.choice(
                len(REGIMES),
                size=params.n_sims,
                p=regime_probs.to_numpy(),
            ),
        )

        company_scenario_rows: list[dict[str, Any]] = []
        portfolio_scenario_rows: list[dict[str, Any]] = []
        base_horizon = min(params.horizons_years)
        base_simulations: list[CompanySimulation] | None = None

        for scenario in params.scenarios:
            regimes = _regime_draws(scenario, draws.base_regimes, params.n_sims)
            for horizon in params.horizons_years:
                simulations = [
                    _simulate_company(
                        company,
                        index,
                        regimes,
                        horizon,
                        draws,
                        params,
                    )
                    for index, company in enumerate(params.companies)
                ]
                if scenario == "base" and horizon == base_horizon:
                    base_simulations = simulations
                for company, simulation in zip(
                    params.companies, simulations, strict=True
                ):
                    company_scenario_rows.append(
                        {
                            "case": f"{company.name}|{scenario}|{horizon}y",
                            **_company_row(company, simulation),
                        }
                    )
                portfolio_scenario_rows.append(
                    {
                        "case": f"{scenario}|{horizon}y",
                        **_portfolio_row(simulations, params.companies),
                    }
                )

        if base_simulations is None:
            raise RuntimeError("base scenario was not simulated")
        score_rows = [
            {"company": company.name, **_company_row(company, simulation)}
            for company, simulation in zip(
                params.companies, base_simulations, strict=True
            )
        ]
        scores = pd.DataFrame(score_rows)

        recoverable_values = np.vstack(
            [simulation.recoverable_amount for simulation in base_simulations]
        )
        if len(params.companies) == 1:
            correlation = np.ones((1, 1))
        else:
            correlation = np.corrcoef(recoverable_values)
        correlation_frame = pd.DataFrame(
            correlation,
            index=[company.name for company in params.companies],
            columns=[company.name for company in params.companies],
        ).reset_index(names="company")

        portfolio_rows = pd.DataFrame(portfolio_scenario_rows)
        base_portfolio = next(
            row for row in portfolio_scenario_rows if row["case"] == f"base|{base_horizon}y"
        )
        metrics = {
            "portfolio_mean_p_impairment": float(scores["p_impairment"].mean()),
            "portfolio_carrying_weighted_p_impairment": float(
                base_portfolio["carrying_weighted_p_impairment"]
            ),
            "portfolio_expected_impairment_loss": float(
                base_portfolio["expected_impairment_loss"]
            ),
            "portfolio_expected_loss_ratio": float(
                base_portfolio["expected_loss_ratio"]
            ),
            "portfolio_loss_p95": float(base_portfolio["loss_p95"]),
            "portfolio_p_any_impairment": float(
                base_portfolio["p_any_impairment"]
            ),
            "portfolio_max_p_impairment": float(scores["p_impairment"].max()),
            "n_companies": float(len(scores)),
            **{f"p_regime_{r}": float(regime_probs[r]) for r in REGIMES},
        }
        for row in portfolio_scenario_rows:
            scenario, horizon = row["case"].split("|")
            metrics[f"{scenario}_{horizon}_expected_loss_ratio"] = float(
                row["expected_loss_ratio"]
            )

        artifacts = [
            ctx.artifacts.publish(
                ctx.run_id,
                "impairment_scores.csv",
                _to_csv(scores),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "scenario_analysis.csv",
                _to_csv(pd.DataFrame(company_scenario_rows)),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "portfolio_scenarios.csv",
                _to_csv(portfolio_rows),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "value_correlation.csv",
                _to_csv(correlation_frame),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "sensitivities.csv",
                _to_csv(pd.DataFrame(_sensitivity_rows(params.companies, base_simulations))),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "financial_resilience.csv",
                _to_csv(pd.DataFrame(_resilience_rows(params.companies))),
            ),
            ctx.artifacts.publish(
                ctx.run_id,
                "regime_probabilities.csv",
                _to_csv(regime_probs.rename_axis("regime").reset_index()),
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


def _to_csv(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n", float_format="%.10g")
    return buf.getvalue().encode()
