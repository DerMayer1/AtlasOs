from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod

from app.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    stage_number: int
    stage_name: str
    timeout_s: int

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        ctx.current_stage = self.stage_number
        logger.info(f"[Stage {self.stage_number}] {self.stage_name} — starting")
        t0 = time.perf_counter()
        try:
            await asyncio.wait_for(self.execute(ctx), timeout=self.timeout_s)
            elapsed = (time.perf_counter() - t0) * 1000
            logger.info(f"[Stage {self.stage_number}] {self.stage_name} — complete ({elapsed:.0f}ms)")
        except asyncio.TimeoutError:
            msg = f"Stage timed out after {self.timeout_s}s"
            ctx.record_error(self.stage_number, self.stage_name, msg)
            logger.error(f"[Stage {self.stage_number}] {self.stage_name} — {msg}")
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            ctx.record_error(self.stage_number, self.stage_name, str(exc))
            logger.error(f"[Stage {self.stage_number}] {self.stage_name} — FAILED ({elapsed:.0f}ms): {exc}")
        return ctx

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> None: ...
