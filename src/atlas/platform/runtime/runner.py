"""Executes one queued analysis: snapshot + engine -> AnalysisResult, persisted.

Used by both the ARQ worker (production) and the in-process queue (dev/tests).
Raises on failure so the queue layer can apply its retry policy; the row is
always left in a consistent state (running -> succeeded | failed).
"""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from atlas.platform.audit.artifacts import ArtifactStore
from atlas.platform.audit.snapshots import SnapshotStore
from atlas.platform.contracts.schemas import AnalysisRequest, utcnow
from atlas.platform.contracts.worker import RunContext
from atlas.platform.db.models import AnalysisRow
from atlas.platform.runtime.registry import EngineRegistry


class AnalysisNotFoundError(Exception):
    pass


def execute_analysis(
    analysis_id: str,
    session_factory: sessionmaker[Session],
    registry: EngineRegistry,
    snapshots: SnapshotStore,
    artifacts: ArtifactStore,
) -> None:
    with session_factory() as session:
        row = session.get(AnalysisRow, analysis_id)
        if row is None:
            raise AnalysisNotFoundError(analysis_id)
        row.status = "running"
        row.attempts += 1
        row.started_at = utcnow()
        session.commit()

        request = AnalysisRequest(
            request_id=row.id,
            engine=row.engine,
            snapshot_id=row.snapshot_id,
            params=row.params,
        )
        try:
            worker = registry.get(row.engine)
            result = worker.run(
                request, RunContext(run_id=row.id, snapshots=snapshots, artifacts=artifacts)
            )
            row.status = "succeeded"
            row.result = result.model_dump(mode="json")
            row.error = None
        except Exception as exc:
            row.status = "failed"
            row.error = f"{type(exc).__name__}: {exc}"
            row.finished_at = utcnow()
            session.commit()
            raise
        row.finished_at = utcnow()
        session.commit()
