"""Agent service: the full orchestrated flow (PRD R7).

plan -> execute engines -> narrate -> validate citations (retry once) -> degrade
if needed -> persist trace. Every branch leaves a trace; the numeric pipeline
never blocks on the LLM.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from atlas.agent import citations, narrator
from atlas.agent.llm import LLMClient, LLMUnavailableError
from atlas.agent.orchestrator import make_plan
from atlas.agent.prompts import PROMPT_VERSION
from atlas.agent.schemas import AgentAnswer, ExecutedCall, Plan, TokenUsage
from atlas.agent.trace_store import TraceStore
from atlas.platform.audit.artifacts import ArtifactStore
from atlas.platform.audit.snapshots import SnapshotStore
from atlas.platform.contracts.schemas import AnalysisResult
from atlas.platform.db.models import AnalysisRow
from atlas.platform.runtime.registry import EngineRegistry
from atlas.platform.runtime.runner import execute_analysis


@dataclass
class AgentService:
    registry: EngineRegistry
    snapshots: SnapshotStore
    artifacts: ArtifactStore
    session_factory: sessionmaker[Session]
    trace_store: TraceStore
    llm: LLMClient

    def ask(
        self,
        question: str,
        snapshot_id: str,
        params: dict,
        portfolio_id: str | None = None,
        portfolio_context: str = "",
    ) -> AgentAnswer:
        t0 = time.monotonic()
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        caps = self.registry.capabilities()

        plan, _used_llm = make_plan(question, self.registry, self.llm, portfolio_context)

        # honest refusal — not a degradation, a correct "cannot" (PRD edge case)
        if plan.is_refusal:
            answer = AgentAnswer(
                trace_id=trace_id, question=question, plan=plan,
                capabilities=caps, llm_model=self.llm.model,
                latency_ms=_elapsed_ms(t0),
            )
            self.trace_store.save(answer, PROMPT_VERSION, portfolio_id)
            return answer

        executed, results = self._run_plan(plan, snapshot_id, params, portfolio_id)
        ok_results = [r for r in results if r is not None]

        narrative, citation_report, degraded, reason, usage = self._narrate(
            question, ok_results
        )

        answer = AgentAnswer(
            trace_id=trace_id, question=question, plan=plan, executed=executed,
            narrative=narrative, citations=citation_report,
            degraded=degraded, degraded_reason=reason,
            capabilities=caps, llm_model=self.llm.model, usage=usage,
            latency_ms=_elapsed_ms(t0),
        )
        self.trace_store.save(answer, PROMPT_VERSION, portfolio_id)
        return answer

    # -- internals ----------------------------------------------------------

    def _run_plan(
        self, plan: Plan, snapshot_id: str, params: dict, portfolio_id: str | None
    ) -> tuple[list[ExecutedCall], list[AnalysisResult | None]]:
        executed: list[ExecutedCall] = []
        results: list[AnalysisResult | None] = []
        for call in plan.calls:
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            with self.session_factory() as session:
                session.add(
                    AnalysisRow(
                        id=run_id, portfolio_id=portfolio_id, engine=call.engine,
                        snapshot_id=snapshot_id, params=params, status="queued",
                    )
                )
                session.commit()

            t0 = time.monotonic()
            try:
                execute_analysis(
                    run_id, self.session_factory, self.registry,
                    self.snapshots, self.artifacts,
                )
            except Exception:
                pass  # failure is persisted on the row; reflected below

            with self.session_factory() as session:
                row = session.get(AnalysisRow, run_id)
                result = AnalysisResult.model_validate(row.result) if row.result else None
                executed.append(
                    ExecutedCall(
                        engine=call.engine, run_id=run_id, status=row.status,
                        latency_ms=_elapsed_ms(t0),
                        result_id=result.result_id if result else None,
                        error=row.error,
                    )
                )
                results.append(result)
        return executed, results

    def _narrate(self, question, ok_results):
        """Returns (narrative, citation_report, degraded, reason, usage)."""
        usage = TokenUsage()
        if not ok_results:
            return None, citations.CitationReport(), True, "all engine runs failed", usage

        # LLM path with one validate-and-retry, then degrade to the template.
        try:
            for _ in range(2):
                text, used = narrator.narrate_with_llm(
                    question, ok_results, self.artifacts, self.llm
                )
                usage = usage + used
                report = citations.validate(text, self.artifacts)
                if report.valid:
                    return text, report, False, None, usage
            # both attempts produced orphan/invalid citations -> numbers-only
            template = narrator.template_narrative(ok_results, self.artifacts)
            return (
                template, citations.validate(template, self.artifacts), True,
                "LLM narrative failed citation validation; degraded to numbers-only", usage,
            )
        except LLMUnavailableError as exc:
            template = narrator.template_narrative(ok_results, self.artifacts)
            return (
                template, citations.validate(template, self.artifacts), True,
                f"LLM unavailable ({exc}); degraded to numbers-only", usage,
            )


def _elapsed_ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)
