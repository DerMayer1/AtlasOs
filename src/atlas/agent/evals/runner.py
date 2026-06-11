"""Eval runner (PRD R8): builds a real AgentService against a temp SQLite + a
synthetic snapshot, runs every case, and reports a pass score. CI fails the
build if the score regresses.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from atlas.agent.evals.cases import CASES, EvalCase
from atlas.agent.llm import LLMClient, ScriptedLLMClient
from atlas.agent.service import AgentService
from atlas.agent.trace_store import TraceStore
from atlas.domain.data.synthetic import make_macro_frame
from atlas.domain.engines import build_registry
from atlas.platform.audit.artifacts import ArtifactStore
from atlas.platform.audit.snapshots import SnapshotStore
from atlas.platform.db.models import Base
from atlas.platform.db.session import make_engine, make_session_factory

_PORTFOLIO_PARAMS = {
    "companies": [
        {"name": "Alpha Industrials", "ebitda": 120.0, "multiple": 8.0, "carrying_value": 900.0},
        {"name": "Beta Logistics", "ebitda": 60.0, "multiple": 6.5, "carrying_value": 450.0},
    ],
    "n_sims": 2000,
    "seed": 7,
}


@dataclass
class CaseResult:
    name: str
    passed: bool
    detail: str


@dataclass
class EvalReport:
    results: list[CaseResult]

    @property
    def passed(self) -> int:
        return sum(r.passed for r in self.results)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def failures(self) -> list[CaseResult]:
        return [r for r in self.results if not r.passed]


def _build_service(root: Path, llm: LLMClient):
    engine = make_engine(f"sqlite:///{root / 'evals.db'}")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    snapshots = SnapshotStore(root / "snapshots")
    artifacts = ArtifactStore(root / "artifacts")
    manifest = snapshots.create({"macro": make_macro_frame()}, sources=["synthetic://eval"])
    service = AgentService(
        registry=build_registry(),
        snapshots=snapshots,
        artifacts=artifacts,
        session_factory=session_factory,
        trace_store=TraceStore(session_factory),
        llm=llm,
    )
    return service, manifest.snapshot_id, engine


def _run_case(case: EvalCase, root: Path) -> CaseResult:
    llm = ScriptedLLMClient(case.responder)
    service, snapshot_id, engine = _build_service(root, llm)
    try:
        answer = service.ask(
            question=case.question,
            snapshot_id=snapshot_id,
            params=dict(_PORTFOLIO_PARAMS),
            portfolio_id="pf_eval",
            portfolio_context="Eval Portfolio: Alpha Industrials, Beta Logistics",
        )
        passed = bool(case.check(answer))
        detail = "" if passed else f"degraded={answer.degraded} reason={answer.degraded_reason}"
    except Exception as exc:  # a check that raises is a failure, not a crash
        passed, detail = False, f"{type(exc).__name__}: {exc}"
    finally:
        engine.dispose()  # release the SQLite file so the tempdir can be removed
    return CaseResult(name=case.name, passed=passed, detail=detail)


def run_evals() -> EvalReport:
    results: list[CaseResult] = []
    for case in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            results.append(_run_case(case, Path(tmp)))
    return EvalReport(results=results)


if __name__ == "__main__":
    import sys

    from atlas.agent.prompts import PROMPT_VERSION

    report = run_evals()
    for r in report.results:
        mark = "PASS" if r.passed else "FAIL"
        print(f"[{mark}] {r.name}  {r.detail}")
    print(f"\nprompt_version: {PROMPT_VERSION}")
    print(f"score: {report.passed}/{report.total} = {report.score:.0%}")
    sys.exit(0 if report.score == 1.0 else 1)  # CI gate: regression blocks merge
