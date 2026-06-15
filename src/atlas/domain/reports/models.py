"""Typed structure of a decision report. Every figure carries a citation so a
later narration can be validated the same way agent answers are (PRD R7)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from atlas.platform.contracts.schemas import utcnow

Severity = Literal["info", "watch", "elevated", "critical"]
FigureFormat = Literal["ratio", "currency", "count", "number"]


class Citation(BaseModel):
    """Points at the exact artifact value behind a figure or action.

    ``artifact`` is the run-local artifact name (e.g. ``metrics.json``);
    ``locator`` is the key or row inside it (e.g. ``portfolio_loss_p95`` or
    ``Alpha.liquidity_gap_1y``). Renders as ``artifact:locator``.
    """

    model_config = ConfigDict(frozen=True)

    artifact: str
    locator: str


class Figure(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    value: float
    format: FigureFormat = "number"
    severity: Severity = "info"
    citation: Citation


class Action(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    title: str
    severity: Severity
    rationale: str
    citations: list[Citation]


class Report(BaseModel):
    report_id: str
    run_id: str
    engine: str
    snapshot_id: str
    engine_version: str
    model_version: str
    headline: str
    key_figures: list[Figure] = Field(default_factory=list)
    risk_drivers: list[Figure] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    previous_run_id: str | None = None
    generated_at: datetime = Field(default_factory=utcnow)
