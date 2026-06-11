"""Job queue abstraction (PRD R3): POST /analyses must answer in <500ms, so
work always goes through a queue interface.

- ArqQueue: production path, Redis-backed, retries handled by the ARQ worker.
- InProcessQueue: dev/tests path (no Redis); executes synchronously and
  swallows engine exceptions because the failure is already persisted on the
  analysis row by the runner — the API contract (poll GET /analyses/{id})
  stays identical in both modes.
"""

from __future__ import annotations

from typing import Protocol

from arq import create_pool
from arq.connections import RedisSettings


class JobQueue(Protocol):
    async def enqueue_analysis(self, analysis_id: str) -> None: ...


class ArqQueue:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._pool = None

    async def enqueue_analysis(self, analysis_id: str) -> None:
        if self._pool is None:
            self._pool = await create_pool(RedisSettings.from_dsn(self._redis_url))
        await self._pool.enqueue_job("run_analysis", analysis_id)


class InProcessQueue:
    def __init__(self, runner) -> None:
        self._runner = runner  # callable(analysis_id) -> None

    async def enqueue_analysis(self, analysis_id: str) -> None:
        try:
            self._runner(analysis_id)
        except Exception:
            pass  # outcome is persisted on the analysis row; clients poll it
