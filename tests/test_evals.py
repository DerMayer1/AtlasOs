"""The agent eval suite gate (PRD R8): CI fails if the score regresses.

This is the test that turns "changing the prompt or agent logic" into a
red build when behaviour regresses."""

from atlas.agent.evals.cases import CASES
from atlas.agent.evals.runner import run_evals


def test_at_least_15_eval_cases():
    assert len(CASES) >= 15  # PRD R8 minimum


def test_eval_suite_passes():
    report = run_evals()
    failures = [f"{r.name}: {r.detail}" for r in report.failures]
    assert report.score == 1.0, f"eval regressions ({report.passed}/{report.total}): {failures}"
