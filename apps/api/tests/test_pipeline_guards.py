"""
Unit tests for pipeline abort chain and guards.
"""
from unittest.mock import patch

import pytest

from app.pipeline.base import PipelineStage
from app.pipeline.context import CompanyInput, PipelineContext


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

    @pytest.mark.asyncio
    async def test_runner_stops_and_emits_failed_event_after_abort(self):
        from app.pipeline import runner

        events = []

        async def on_event(event, data):
            events.append((event, data))

        with patch.object(runner, "STAGES", [MockCriticalStage(), MockNonCriticalStage()]):
            MockNonCriticalStage.executed = False
            ctx = await runner.run_pipeline(make_ctx().input, on_event=on_event)

        assert ctx.aborted is True
        assert MockNonCriticalStage.executed is False
        assert [event for event, _ in events] == ["stage_start", "stage_failed"]
