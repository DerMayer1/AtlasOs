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
    # If True, pipeline aborts all subsequent LLM stages when this one fails.
    # Set on stages whose output is required by everything downstream.
    is_critical: bool = False

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        # Abort early if a previous critical stage already failed
        if ctx.aborted:
            logger.warning(
                f"[Stage {self.stage_number}] {self.stage_name} — SKIPPED "
                f"(pipeline aborted at stage {ctx.abort_stage})"
            )
            return ctx

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
            if self.is_critical:
                ctx.abort(self.stage_number)
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            ctx.record_error(self.stage_number, self.stage_name, str(exc))
            logger.error(f"[Stage {self.stage_number}] {self.stage_name} — FAILED ({elapsed:.0f}ms): {exc}")
            if self.is_critical:
                ctx.abort(self.stage_number)
        return ctx

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> None: ...
