"""Typed financial inputs for the impairment engine."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ScenarioName = Literal["base", "tightening", "crisis"]


class CompanyFinancialProfile(BaseModel):
    """Financial and risk assumptions for one portfolio company.

    The original four fields remain sufficient. Additional fields make the
    valuation distribution and the separate resilience diagnostics explicit.
    """

    name: str = Field(min_length=1, max_length=200)
    sector: str = Field(default="general", min_length=1, max_length=100)
    geography: str = Field(default="global", min_length=1, max_length=100)
    ebitda: float = Field(gt=0)
    multiple: float = Field(gt=0)
    carrying_value: float = Field(gt=0)

    ebitda_margin: float | None = Field(default=None, gt=0, le=1)
    ebitda_volatility: float = Field(default=0.30, gt=0, le=1.5)
    macro_sensitivity: float = Field(default=1.0, ge=0, le=3.0)
    sector_sensitivity: float = Field(default=1.0, ge=0, le=3.0)

    multiple_volatility: float = Field(default=0.18, ge=0, le=1.0)
    multiple_floor: float | None = Field(default=None, gt=0)
    multiple_ceiling: float | None = Field(default=None, gt=0)

    debt: float = Field(default=0.0, ge=0)
    cash: float = Field(default=0.0, ge=0)
    annual_interest_expense: float | None = Field(default=None, ge=0)
    interest_rate: float = Field(default=0.08, ge=0, le=1)
    debt_due_1y: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def validate_multiple_range(self) -> CompanyFinancialProfile:
        floor = self.resolved_multiple_floor
        ceiling = self.resolved_multiple_ceiling
        if floor >= ceiling:
            raise ValueError("multiple_floor must be lower than multiple_ceiling")
        if not floor <= self.multiple <= ceiling:
            raise ValueError("multiple must be inside the configured multiple range")
        return self

    @property
    def resolved_multiple_floor(self) -> float:
        return self.multiple_floor if self.multiple_floor is not None else self.multiple * 0.55

    @property
    def resolved_multiple_ceiling(self) -> float:
        return self.multiple_ceiling if self.multiple_ceiling is not None else self.multiple * 1.25

    @property
    def resolved_interest_expense(self) -> float:
        if self.annual_interest_expense is not None:
            return self.annual_interest_expense
        return self.debt * self.interest_rate


class ImpairmentParams(BaseModel):
    companies: list[CompanyFinancialProfile] = Field(min_length=1)
    n_sims: int = Field(default=10_000, ge=100, le=1_000_000)
    seed: int = Field(default=0, ge=0)
    regime_model: Literal["hmm", "zscore"] = "hmm"
    scenarios: list[ScenarioName] = Field(
        default_factory=lambda: ["base", "tightening", "crisis"]
    )
    horizons_years: list[Literal[1, 3]] = Field(default_factory=lambda: [1, 3])

    # Variance shares in the EBITDA factor model. The residual is company
    # specific, so cross-company dependence is explicit but never perfect.
    market_variance_share: float = Field(default=0.35, ge=0, lt=1)
    sector_variance_share: float = Field(default=0.25, ge=0, lt=1)
    multiple_ebitda_correlation: float = Field(default=0.55, ge=-0.95, le=0.95)

    @model_validator(mode="after")
    def validate_simulation_design(self) -> ImpairmentParams:
        if self.market_variance_share + self.sector_variance_share >= 1:
            raise ValueError(
                "market_variance_share + sector_variance_share must be lower than 1"
            )
        if "base" not in self.scenarios:
            raise ValueError("scenarios must include 'base'")
        if len(set(self.scenarios)) != len(self.scenarios):
            raise ValueError("scenarios must not contain duplicates")
        if len(set(self.horizons_years)) != len(self.horizons_years):
            raise ValueError("horizons_years must not contain duplicates")
        return self
