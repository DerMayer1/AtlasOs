"""FastAPI application (PRD R3). P0 endpoints:

POST /portfolios, POST /analyses, GET /analyses/{id},
POST /agent/ask, GET /artifacts/{run_id}/{name}, GET /health
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from atlas.interfaces.api.auth import SCOPE_READ, SCOPE_RUN, require_scope
from atlas.interfaces.api.container import Container, build_container
from atlas.platform.audit.snapshots import SnapshotNotFoundError
from atlas.platform.db.models import AnalysisRow, PortfolioRow, SnapshotRow
from atlas.platform.runtime.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Atlas", version="0.1.0")
    app.state.container = build_container(settings or get_settings())
    app.include_router(_router())
    return app


def _container(request: Request) -> Container:
    return request.app.state.container


# --- request/response models -------------------------------------------------


class CompanyIn(BaseModel):
    name: str
    ebitda: float = Field(gt=0)
    multiple: float = Field(gt=0, default=8.0)
    carrying_value: float = Field(gt=0)


class PortfolioIn(BaseModel):
    name: str
    companies: list[CompanyIn] = Field(min_length=1)


class AnalysisIn(BaseModel):
    engine: str = "impairment"
    portfolio_id: str | None = None
    snapshot_id: str | None = None  # default: latest registered snapshot
    params: dict[str, Any] = Field(default_factory=dict)


class AgentAskIn(BaseModel):
    question: str
    portfolio_id: str | None = None
    snapshot_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


def _router():
    from fastapi import APIRouter

    router = APIRouter()

    @router.post("/portfolios", status_code=201, dependencies=[require_scope(SCOPE_RUN)])
    def create_portfolio(body: PortfolioIn, request: Request):
        c = _container(request)
        row = PortfolioRow(
            id=f"pf_{uuid.uuid4().hex[:12]}",
            name=body.name,
            companies=[co.model_dump() for co in body.companies],
        )
        with c.session_factory() as session:
            session.add(row)
            session.commit()
        return {"portfolio_id": row.id, "name": row.name, "companies": row.companies}

    @router.get("/portfolios/{portfolio_id}", dependencies=[require_scope(SCOPE_READ)])
    def get_portfolio(portfolio_id: str, request: Request):
        c = _container(request)
        with c.session_factory() as session:
            row = session.get(PortfolioRow, portfolio_id)
        if row is None:
            raise HTTPException(404, "portfolio not found")
        return {"portfolio_id": row.id, "name": row.name, "companies": row.companies}

    @router.post("/analyses", status_code=202, dependencies=[require_scope(SCOPE_RUN)])
    async def create_analysis(body: AnalysisIn, request: Request):
        c = _container(request)
        with c.session_factory() as session:
            if body.engine not in c.registry.capabilities():
                raise HTTPException(
                    422,
                    f"unknown engine {body.engine!r}; "
                    f"available: {sorted(c.registry.capabilities())}",
                )

            params = dict(body.params)
            if body.portfolio_id:
                portfolio = session.get(PortfolioRow, body.portfolio_id)
                if portfolio is None:
                    raise HTTPException(404, "portfolio not found")
                params.setdefault("companies", portfolio.companies)

            snapshot_id = body.snapshot_id
            if snapshot_id is None:
                latest = session.execute(
                    select(SnapshotRow).order_by(SnapshotRow.created_at.desc()).limit(1)
                ).scalar_one_or_none()
                if latest is None:
                    raise HTTPException(
                        409,
                        "no snapshot available; analyses never run on live data "
                        "(create one via the CLI: python -m atlas.interfaces.cli seed)",
                    )
                snapshot_id = latest.snapshot_id
            else:
                try:
                    c.snapshots.manifest(snapshot_id)
                except SnapshotNotFoundError:
                    raise HTTPException(404, f"snapshot {snapshot_id!r} not found") from None

            row = AnalysisRow(
                id=f"run_{uuid.uuid4().hex[:12]}",
                portfolio_id=body.portfolio_id,
                engine=body.engine,
                snapshot_id=snapshot_id,
                params=params,
                status="queued",
            )
            session.add(row)
            session.commit()
            job_id = row.id

        await c.queue.enqueue_analysis(job_id)
        return {"job_id": job_id, "status": "queued"}

    @router.get("/analyses/{analysis_id}", dependencies=[require_scope(SCOPE_READ)])
    def get_analysis(analysis_id: str, request: Request):
        c = _container(request)
        with c.session_factory() as session:
            row = session.get(AnalysisRow, analysis_id)
        if row is None:
            raise HTTPException(404, "analysis not found")
        return {
            "job_id": row.id,
            "engine": row.engine,
            "snapshot_id": row.snapshot_id,
            "status": row.status,
            "attempts": row.attempts,
            "error": row.error,
            "result": row.result,
            "created_at": row.created_at,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
        }

    @router.post("/agent/ask", dependencies=[require_scope(SCOPE_RUN)])
    def agent_ask(body: AgentAskIn, request: Request):
        c = _container(request)
        params = dict(body.params)
        portfolio_context = ""

        with c.session_factory() as session:
            if body.portfolio_id:
                portfolio = session.get(PortfolioRow, body.portfolio_id)
                if portfolio is None:
                    raise HTTPException(404, "portfolio not found")
                params.setdefault("companies", portfolio.companies)
                names = [co.get("name", "?") for co in portfolio.companies]
                portfolio_context = f"{portfolio.name}: {', '.join(names)}"

            snapshot_id = body.snapshot_id
            if snapshot_id is None:
                latest = session.execute(
                    select(SnapshotRow).order_by(SnapshotRow.created_at.desc()).limit(1)
                ).scalar_one_or_none()
                if latest is None:
                    raise HTTPException(
                        409, "no snapshot available; analyses never run on live data"
                    )
                snapshot_id = latest.snapshot_id
            else:
                try:
                    c.snapshots.manifest(snapshot_id)
                except SnapshotNotFoundError:
                    raise HTTPException(404, f"snapshot {snapshot_id!r} not found") from None

        answer = c.agent.ask(
            question=body.question,
            snapshot_id=snapshot_id,
            params=params,
            portfolio_id=body.portfolio_id,
            portfolio_context=portfolio_context,
        )
        return answer.model_dump(mode="json")

    @router.get("/agent/traces/{trace_id}", dependencies=[require_scope(SCOPE_READ)])
    def get_trace(trace_id: str, request: Request):
        c = _container(request)
        row = c.agent.trace_store.get(trace_id)
        if row is None:
            raise HTTPException(404, "trace not found")
        return {
            "trace_id": row.id,
            "question": row.question,
            "plan": row.plan,
            "executed": row.executed,
            "run_ids": row.run_ids,
            "narrative": row.narrative,
            "citations": row.citations,
            "citations_valid": row.citations_valid,
            "degraded": row.degraded,
            "degraded_reason": row.degraded_reason,
            "prompt_version": row.prompt_version,
            "llm_model": row.llm_model,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "cost_usd": row.cost_usd,
            "latency_ms": row.latency_ms,
            "created_at": row.created_at,
        }

    @router.get(
        "/artifacts/{run_id}/{name}",
        dependencies=[require_scope(SCOPE_READ)],
    )
    def get_artifact(run_id: str, name: str, request: Request):
        c = _container(request)
        try:
            path = c.artifacts.open_path(f"{run_id}/{name}")
        except FileNotFoundError:
            raise HTTPException(404, "artifact not found") from None
        return FileResponse(path, filename=name)

    @router.get("/health")
    def health(request: Request):
        c = _container(request)
        checks: dict[str, str] = {}
        try:
            with c.session_factory() as session:
                session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {type(exc).__name__}"

        if c.settings.redis_url:
            try:
                import redis as redis_lib

                redis_lib.from_url(c.settings.redis_url).ping()
                checks["queue"] = "ok"
            except Exception as exc:
                checks["queue"] = f"error: {type(exc).__name__}"
        else:
            checks["queue"] = "in-process"

        try:
            import httpx

            from atlas.domain.data.fred import FREDGRAPH_URL

            resp = httpx.head(FREDGRAPH_URL, params={"id": "FEDFUNDS"}, timeout=3.0)
            checks["fred"] = "ok" if resp.status_code < 500 else f"error: {resp.status_code}"
        except Exception as exc:
            checks["fred"] = f"error: {type(exc).__name__}"

        # fred is informational: an outage degrades ingestion, not the API
        # (scheduled analyses fall back to the last valid snapshot, PRD §5).
        core = (checks["database"], checks["queue"])
        status = "ok" if all(not v.startswith("error") for v in core) else "degraded"
        return {"status": status, "checks": checks}

    return router


# uvicorn entrypoint: uvicorn atlas.interfaces.api.app:create_app --factory
