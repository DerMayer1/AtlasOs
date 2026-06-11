"""Central platform contracts (PRD R1).

Every engine speaks these schemas and nothing else. Breaking changes to any
model here require a CONTRACT_VERSION bump.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0.0"


def utcnow() -> datetime:
    return datetime.now(UTC)


class ArtifactKind(enum.StrEnum):
    CSV = "csv"
    PARQUET = "parquet"
    JSON = "json"
    PNG = "png"


class Artifact(BaseModel):
    """An addressable numeric output of a run. Narratives cite these by id."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    run_id: str
    name: str
    kind: ArtifactKind
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    created_at: datetime = Field(default_factory=utcnow)


class SnapshotTable(BaseModel):
    """One frozen table inside a snapshot."""

    model_config = ConfigDict(frozen=True)

    name: str
    file: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rows: int = Field(ge=0)


class SnapshotManifest(BaseModel):
    """Identity card of an immutable data snapshot (PRD R2)."""

    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    created_at: datetime
    sources: list[str]
    period_start: str | None = None
    period_end: str | None = None
    tables: list[SnapshotTable]
    contract_version: str = CONTRACT_VERSION


class AnalysisStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AnalysisRequest(BaseModel):
    """What a caller asks an engine to do. No live data: snapshot_id is mandatory."""

    request_id: str
    engine: str
    snapshot_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=utcnow)
    contract_version: str = CONTRACT_VERSION


class AnalysisResult(BaseModel):
    """What every engine returns. Carries full provenance (PRD R1 acceptance)."""

    result_id: str
    request_id: str
    run_id: str
    engine: str
    engine_version: str
    model_version: str
    snapshot_id: str
    status: AnalysisStatus
    started_at: datetime
    finished_at: datetime | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    error: str | None = None
    contract_version: str = CONTRACT_VERSION


class TraceEvent(BaseModel):
    """One step of an agent/orchestrator decision (full agent lands in Phase 3)."""

    ts: datetime = Field(default_factory=utcnow)
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)


class Trace(BaseModel):
    trace_id: str
    run_id: str
    events: list[TraceEvent] = Field(default_factory=list)
    contract_version: str = CONTRACT_VERSION
