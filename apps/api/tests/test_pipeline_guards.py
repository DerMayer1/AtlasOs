"""
Unit tests for pipeline abort chain and guards.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.pipeline.context import CompanyInput, PipelineContext
from app.pipeline.base import PipelineStage


class MockCriticalStage(PipelineStage):
    stage_number = 1
    stage_name = "Mock Critical"
    timeout_s = 5
    is_critical = True

    async def execute(self, ctx: PipelineContext) -> None:
        raise RuntimeError("Simulated critical failure")


class MockNonCriticalStage(PipelineStage):
    stage_number = 2
    stage_name = "Mock Non-Critical"
    timeout_s = 5
    is_critical = False
    executed: bool = False

    async def execute(self, ctx: PipelineContext) -> None:
        MockNonCriticalStage.executed = True


def make_ctx() -> PipelineContext:
    return PipelineContext(
        input=CompanyInput(
            company_name="Test",
            website_url="https://example.com",
            description="A test company.",
        )
    )


class TestAbortChain:
    @pytest.mark.asyncio
    async def test_critical_failure_sets_aborted(self):
        ctx = make_ctx()
        stage = MockCriticalStage()
        await stage.run(ctx)
        assert ctx.aborted is True
        assert ctx.abort_stage == 1
        assert len(ctx.errors) == 1

    @pytest.mark.asyncio
    async def test_subsequent_stage_skipped_after_abort(self):
        ctx = make_ctx()
        ctx.abort(1)  # Simulate prior abort

        MockNonCriticalStage.executed = False
        stage = MockNonCriticalStage()
        await stage.run(ctx)

        assert MockNonCriticalStage.executed is False

    @pytest.mark.asyncio
    async def test_non_critical_failure_does_not_abort(self):
        class FailingNonCritical(PipelineStage):
            stage_number = 3
            stage_name = "Failing Non-Critical"
            timeout_s = 5
            is_critical = False

            async def execute(self, ctx: PipelineContext) -> None:
                raise RuntimeError("Non-critical failure")

        ctx = make_ctx()
        stage = FailingNonCritical()
        await stage.run(ctx)

        assert ctx.aborted is False
        assert len(ctx.errors) == 1
