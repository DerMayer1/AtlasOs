"""The AnalysisWorker interface every engine implements (PRD R1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from atlas.platform.audit.artifacts import ArtifactStore
    from atlas.platform.audit.snapshots import SnapshotStore
    from atlas.platform.contracts.schemas import AnalysisRequest, AnalysisResult


@dataclass(frozen=True)
class RunContext:
    """Everything an engine is allowed to touch: frozen data in, artifacts out."""

    run_id: str
    snapshots: SnapshotStore
    artifacts: ArtifactStore


@runtime_checkable
class AnalysisWorker(Protocol):
    """Engines produce numbers from a snapshot. Nothing else.

    Implementations must be deterministic given (snapshot_id, params with seed).
    """

    name: str
    engine_version: str
    model_version: str

    def describe(self) -> str:
        """Human-readable capability summary (used by the agent registry)."""
        ...

    def run(self, request: AnalysisRequest, ctx: RunContext) -> AnalysisResult: ...
