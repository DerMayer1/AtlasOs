"""Postgres is the source of truth (PRD R3). Payload columns are JSON so the
platform stays domain-agnostic; the API layer interprets their shape.

org_id columns are nullable placeholders for multi-tenancy (PRD P2): present in
the schema from day one, no logic implemented.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from atlas.platform.contracts.schemas import utcnow


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


class PortfolioRow(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    companies: Mapped[list[Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AnalysisRow(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # doubles as run_id
    org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    portfolio_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engine: Mapped[str] = mapped_column(String(100))
    snapshot_id: Mapped[str] = mapped_column(String(100))
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
    org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 of the token
    scopes: Mapped[str] = mapped_column(String(100))  # comma-separated: "read,run"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
