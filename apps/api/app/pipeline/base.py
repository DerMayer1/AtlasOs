from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod

from app.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)

RETRY_DELAY_S = 2.0  # backoff before retry attempt


class PipelineStage(ABC):
    stage_number: int
    stage_name: str
    timeout_s: int
    is_critical: bool = False   # abort pipeline on failure if True
    max_retries: int = 0        # non-critical stages may retry once

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.aborted:
            logger.warning(
                f"[Stage {self.stage_number}] {self.stage_name} — SKIPPED "
                f"(pipeline aborted at stage {ctx.abort_stage})"
            )
            return ctx

        ctx.current_stage = self.stage_number
        attempts = 0
        max_attempts = 1 + (self.max_retries if not self.is_critical else 0)

        while attempts < max_attempts:
            attempts += 1
            attempt_label = f"attempt {attempts}/{max_attempts}" if max_attempts > 1 else ""
            logger.info(f"[Stage {self.stage_number}] {self.stage_name} — starting {attempt_label}".strip())
            t0 = time.perf_counter()

            try:
                await asyncio.wait_for(self.execute(ctx), timeout=self.timeout_s)
                elapsed = (time.perf_counter() - t0) * 1000
                logger.info(f"[Stage {self.stage_number}] {self.stage_name} — complete ({elapsed:.0f}ms)")
                return ctx  # success — exit retry loop

            except asyncio.TimeoutError:
                elapsed = (time.perf_counter() - t0) * 1000
                msg = f"Stage timed out after {self.timeout_s}s"
                logger.error(f"[Stage {self.stage_number}] {self.stage_name} — {msg} ({elapsed:.0f}ms)")
                if attempts >= max_attempts:
                    ctx.record_error(self.stage_number, self.stage_name, msg)
                    if self.is_critical:
                        ctx.abort(self.stage_number)
                else:
                    logger.info(f"[Stage {self.stage_number}] Retrying in {RETRY_DELAY_S}s...")
                    await asyncio.sleep(RETRY_DELAY_S)

            except Exception as exc:
                elapsed = (time.perf_counter() - t0) * 1000
                logger.error(f"[Stage {self.stage_number}] {self.stage_name} — FAILED ({elapsed:.0f}ms): {exc}")
                if attempts >= max_attempts:
                    ctx.record_error(self.stage_number, self.stage_name, str(exc))
                    if self.is_critical:
                        ctx.abort(self.stage_number)
                else:
                    logger.info(f"[Stage {self.stage_number}] Retrying in {RETRY_DELAY_S}s...")
                    await asyncio.sleep(RETRY_DELAY_S)

        return ctx

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> None: ...
