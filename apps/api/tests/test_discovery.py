from unittest.mock import patch

import pytest

from app.pipeline.context import CompanyInput
from app.pipeline.discovery import run_discovery


@pytest.mark.asyncio
async def test_discovery_runs_only_first_four_stages():
    calls = []

    class Stage:
        def __init__(self, number: int) -> None:
            self.stage_number = number

        async def run(self, ctx):
            calls.append(self.stage_number)
            return ctx

    company = CompanyInput(
        company_name="Test",
        website_url="https://example.com",
        description="Test company",
    )

    with patch(
        "app.pipeline.discovery.DISCOVERY_STAGES",
        [Stage(1), Stage(2), Stage(3), Stage(4)],
    ):
        await run_discovery(company)

    assert calls == [1, 2, 3, 4]
