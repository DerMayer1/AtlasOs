"""ARQ worker: consumes analysis jobs from Redis (PRD R3).

Retry policy: 3 tries with exponential backoff (2^attempt seconds). After the
final try the analysis row stays 'failed' with the persisted error — queryable
via GET /analyses/{id}.

Run: arq atlas.interfaces.worker.WorkerSettings
"""

from __future__ import annotations

import asyncio
from functools import partial

from arq.connections import RedisSettings
from arq.worker import Retry

from atlas.domain.engines import build_registry
from atlas.platform.audit.artifacts import ArtifactStore
from atlas.platform.audit.snapshots import SnapshotStore
from atlas.platform.db.session import make_engine, make_session_factory
from atlas.platform.runtime.runner import execute_analysis
from atlas.platform.runtime.settings import get_settings

_settings = get_settings()


async def startup(ctx: dict) -> None:
    engine = make_engine(_settings.database_url)
    ctx["session_factory"] = make_session_factory(engine)
    ctx["registry"] = build_registry()
    ctx["snapshots"] = SnapshotStore(_settings.data_dir / "snapshots")
    ctx["artifacts"] = ArtifactStore(_settings.data_dir / "artifacts")


async def run_analysis(ctx: dict, analysis_id: str) -> None:
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None,
            partial(
                execute_analysis,
                analysis_id,
                ctx["session_factory"],
                ctx["registry"],
                ctx["snapshots"],
                ctx["artifacts"],
            ),
        )
    except Exception:
        attempt = ctx["job_try"]
        if attempt < _settings.job_max_tries:
            raise Retry(defer=2**attempt) from None
        raise


class WorkerSettings:
    functions = [run_analysis]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(_settings.redis_url or "redis://localhost:6379")
    max_tries = _settings.job_max_tries
