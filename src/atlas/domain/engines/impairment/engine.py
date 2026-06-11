"""Engine 1 — Impairment (PRD R5).

Pipeline per run:
  1. Load the frozen macro table from the referenced snapshot (never live data).
  2. Compute regime probabilities (regimes.py).
  3. Regime-conditional Monte Carlo on each company's EBITDA shock; enterprise
     value = shocked EBITDA x multiple; impaired when EV < carrying value.
  4. Publish addressable artifacts and return an AnalysisResult with metrics.

Determinism: a single numpy Generator seeded from params["seed"] drives all
sampling; same snapshot + same params => bit-identical artifacts.
"""

from __future__ import annotations

import io
import json
import uuid
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from atlas.domain.engines.impairment.hmm import regime_probabilities_hmm
from atlas.domain.engines.impairment.regimes import REGIMES, regime_probabilities
from atlas.platform.contracts.schemas import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatus,
    utcnow,
)
from atlas.platform.contracts.worker import RunContext

# EBITDA growth shock per regime: (mean, std). Phase 2 will calibrate these by
# historical regression for the validation report (PRD Q2); current values are
# placeholders flagged in docs/limitations.md.
_SHOCKS = {
    "expansion": (0.05, 0.08),
    "tightening": (-0.02, 0.12),
    "crisis": (-0.15, 0.20),
}


class Company(BaseModel):
    name: str
    ebitda: float = Field(gt=0)
    multiple: float = Field(gt=0, default=8.0)
    carrying_value: float = Field(gt=0)


class ImpairmentParams(BaseModel):
    companies: list[Company] = Field(min_length=1)
    n_sims: int = Field(default=10_000, ge=100, le=1_000_000)
    seed: int = Field(default=0, ge=0)
    # hmm = production model (Phase 2); zscore = Phase 0 baseline, kept as the
    # comparison model for the validation report.
    regime_model: Literal["hmm", "zscore"] = "hmm"


class ImpairmentEngine:
    name = "impairment"
    engine_version = "0.3.0"
    model_version = "hmm3-mc-0.2"

    def describe(self) -> str:
        return (
            "Portfolio impairment risk: regime-conditional Monte Carlo on EBITDA, "
            "P(impairment) per company plus macro regime probabilities."
        )

    def run(self, request: AnalysisRequest, ctx: RunContext) -> AnalysisResult:
        started = utcnow()
        params = ImpairmentParams.model_validate(request.params)

        tables = ctx.snapshots.load(request.snapshot_id)
        if "macro" not in tables:
            raise ValueError(f"snapshot {request.snapshot_id} has no 'macro' table")

        if params.regime_model == "hmm":
            regime_probs = regime_probabilities_hmm(tables["macro"])
        else:
            regime_probs = regime_probabilities(tables["macro"])
        rng = np.random.default_rng(params.seed)

        regime_draws = rng.choice(len(REGIMES), size=params.n_sims, p=regime_probs.to_numpy())
        mus = np.array([_SHOCKS[r][0] for r in REGIMES])[regime_draws]
        sigmas = np.array([_SHOCKS[r][1] for r in REGIMES])[regime_draws]
        growth = rng.standard_normal(params.n_sims) * sigmas + mus

        rows: list[dict[str, Any]] = []
        for company in params.companies:
            ev = company.ebitda * (1.0 + growth) * company.multiple
            p_imp = float(np.mean(ev < company.carrying_value))
            rows.append(
                {
                    "company": company.name,
                    "p_impairment": p_imp,
                    "ev_mean": float(ev.mean()),
                    "ev_p05": float(np.percentile(ev, 5)),
                    "ev_p95": float(np.percentile(ev, 95)),
                    "carrying_value": company.carrying_value,
                }
            )
        scores = pd.DataFrame(rows)

        metrics = {
            "portfolio_mean_p_impairment": float(scores["p_impairment"].mean()),
            "portfolio_max_p_impairment": float(scores["p_impairment"].max()),
            "n_companies": float(len(scores)),
            **{f"p_regime_{r}": float(regime_probs[r]) for r in REGIMES},
        }

        # metrics.json makes portfolio-level figures addressable so the agent
        # narrator can cite them (PRD R7: every claim cites an artifact).
        artifacts = [
            ctx.artifacts.publish(ctx.run_id, "impairment_scores.csv", _to_csv(scores)),
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
