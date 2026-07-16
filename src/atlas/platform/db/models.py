"""Postgres is the source of truth (PRD R3), scoped by organization."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from atlas.platform.contracts.schemas import utcnow


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


class OrganizationRow(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PortfolioRow(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), default="org_default", index=True)
    name: Mapped[str] = mapped_column(String(200))
    companies: Mapped[list[Any]] = mapped_column(JSON)
    current_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PortfolioVersionRow(Base):
    """Immutable header for one frozen set of portfolio assumptions."""

    __tablename__ = "portfolio_versions"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "version_number",
            name="uq_portfolio_versions_portfolio_number",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("portfolios.id"),
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer)
    portfolio_name: Mapped[str] = mapped_column(String(200))
    input_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PortfolioCompanyInputRow(Base):
    """Normalized, immutable financial input belonging to a portfolio version."""

    __tablename__ = "portfolio_company_inputs"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_version_id",
            "position",
            name="uq_portfolio_company_inputs_version_position",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    portfolio_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("portfolio_versions.id"),
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(100))
    geography: Mapped[str] = mapped_column(String(100))
    ebitda: Mapped[float] = mapped_column(Float)
    multiple: Mapped[float] = mapped_column(Float)
    carrying_value: Mapped[float] = mapped_column(Float)
    ebitda_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    ebitda_history: Mapped[list[Any]] = mapped_column(JSON, default=list)
    ebitda_volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    macro_sensitivity: Mapped[float] = mapped_column(Float)
    sector_sensitivity: Mapped[float] = mapped_column(Float)
    multiple_volatility: Mapped[float] = mapped_column(Float)
    multiple_floor: Mapped[float | None] = mapped_column(Float, nullable=True)
    multiple_ceiling: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt: Mapped[float] = mapped_column(Float)
    cash: Mapped[float] = mapped_column(Float)
    annual_interest_expense: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_rate: Mapped[float] = mapped_column(Float)
    debt_due_1y: Mapped[float] = mapped_column(Float)


class AnalysisRow(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # doubles as run_id
    org_id: Mapped[str] = mapped_column(String(64), default="org_default", index=True)
    portfolio_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    portfolio_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("portfolio_versions.id"),
        nullable=True,
        index=True,
    )
    engine: Mapped[str] = mapped_column(String(100))
    snapshot_id: Mapped[str] = mapped_column(String(100))
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    # sha256 over (engine, engine/model version, snapshot, params): identical
    # requests collapse onto one run instead of re-executing the engine.
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportRow(Base):
    """A deterministic decision report built from one analysis (PRD §7.1).

    ``content`` is the structured Report (figures, drivers, cited actions) — it
    is small operational data, not heavy simulation output, so it lives in
    Postgres where it is queryable; the underlying numbers stay in artifacts."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analyses.id"),
        index=True,
    )
    org_id: Mapped[str] = mapped_column(String(64), default="org_default", index=True)
    engine: Mapped[str] = mapped_column(String(100))
    headline: Mapped[str] = mapped_column(Text)
    action_count: Mapped[int] = mapped_column(Integer, default=0)
    max_severity: Mapped[str] = mapped_column(String(20), default="info")
    previous_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    # Optional AI narrative ANNOTATION (PRD: the LLM explains, never calculates).
    # Kept separate from the deterministic `content`: figures and actions never
    # depend on it, and the trace (degraded, model) records how it was produced.
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_degraded: Mapped[bool] = mapped_column(default=False)
    narrative_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SnapshotRow(Base):
    """Queryable index of snapshots; the files themselves live in SnapshotStore."""

    __tablename__ = "snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentTraceRow(Base):
    """Persisted agent decision (PRD R7): plan, calls, narrative, cost — the
    audit record answering 'why did the system say X on day Y?'.

    Queryable by run, portfolio or period via TraceStore."""

    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), default="org_default", index=True)
    portfolio_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    plan: Mapped[dict[str, Any]] = mapped_column(JSON)
    executed: Mapped[list[Any]] = mapped_column(JSON)
    run_ids: Mapped[list[Any]] = mapped_column(JSON)  # for query-by-run
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[dict[str, Any]] = mapped_column(JSON)
    citations_valid: Mapped[bool] = mapped_column(default=False)
    degraded: Mapped[bool] = mapped_column(default=False)
    degraded_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApiKeyRow(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), default="org_default", index=True)
    name: Mapped[str] = mapped_column(String(200))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 of the token
    scopes: Mapped[str] = mapped_column(String(100))  # comma-separated: "read,run"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
