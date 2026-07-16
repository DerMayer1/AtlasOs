"""Trace store (PRD R7): persist and query agent decisions.

Answers "why did the system say X on day Y?" — by run, by portfolio, by period.
Lives in the agent layer (it knows about AgentAnswer); the table itself is
declared in platform.db.models, the relational source of truth.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from atlas.agent.schemas import AgentAnswer
from atlas.platform.db.models import AgentTraceRow


class TraceStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def save(
        self,
        answer: AgentAnswer,
        prompt_version: str,
        portfolio_id: str | None = None,
        org_id: str = "org_default",
    ) -> None:
        row = AgentTraceRow(
            id=answer.trace_id,
            org_id=org_id,
            portfolio_id=portfolio_id,
            question=answer.question,
            plan=answer.plan.model_dump(mode="json"),
            executed=[e.model_dump(mode="json") for e in answer.executed],
            run_ids=[e.run_id for e in answer.executed],
            narrative=answer.narrative,
            citations=answer.citations.model_dump(mode="json"),
            citations_valid=answer.citations.valid,
            degraded=answer.degraded,
            degraded_reason=answer.degraded_reason,
            prompt_version=prompt_version,
            llm_model=answer.llm_model,
            input_tokens=answer.usage.input_tokens,
            output_tokens=answer.usage.output_tokens,
            cost_usd=answer.usage.cost_usd,
            latency_ms=answer.latency_ms,
        )
        with self._sf() as session:
            session.add(row)
            session.commit()

    def get(self, trace_id: str, org_id: str = "org_default") -> AgentTraceRow | None:
        with self._sf() as session:
            return session.execute(
                select(AgentTraceRow).where(
                    AgentTraceRow.id == trace_id, AgentTraceRow.org_id == org_id
                )
            ).scalar_one_or_none()

    def by_portfolio(
        self, portfolio_id: str, org_id: str = "org_default"
    ) -> list[AgentTraceRow]:
        with self._sf() as session:
            return list(
                session.execute(
                    select(AgentTraceRow)
                    .where(
                        AgentTraceRow.portfolio_id == portfolio_id,
                        AgentTraceRow.org_id == org_id,
                    )
                    .order_by(AgentTraceRow.created_at.desc())
                ).scalars()
            )

    def by_run(self, run_id: str, org_id: str = "org_default") -> list[AgentTraceRow]:
        with self._sf() as session:
            rows = session.execute(
                select(AgentTraceRow).where(AgentTraceRow.org_id == org_id)
            ).scalars()
            return [r for r in rows if run_id in (r.run_ids or [])]

    def by_period(
        self, start: datetime, end: datetime, org_id: str = "org_default"
    ) -> list[AgentTraceRow]:
        with self._sf() as session:
            return list(
                session.execute(
                    select(AgentTraceRow)
                    .where(AgentTraceRow.created_at >= start)
                    .where(AgentTraceRow.created_at <= end)
                    .where(AgentTraceRow.org_id == org_id)
                    .order_by(AgentTraceRow.created_at.desc())
                ).scalars()
            )
