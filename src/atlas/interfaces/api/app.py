"""FastAPI application (PRD R3). P0 endpoints:

POST /portfolios, POST /analyses, GET /analyses/{id},
POST /agent/ask, GET /artifacts/{run_id}/{name}, GET /health
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from atlas.domain.engines.impairment.models import CompanyFinancialProfile
from atlas.domain.reports.builder import build_report
from atlas.interfaces.api.auth import (
    API_KEY_COOKIE,
    DEFAULT_ORG_ID,
    SCOPE_READ,
    SCOPE_RUN,
    create_api_key,
    hash_token,
    require_scope,
)
from atlas.interfaces.api.container import Container, build_container
from atlas.interfaces.api.security import (
    MaxBodySizeMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from atlas.platform.audit.snapshots import SnapshotNotFoundError
from atlas.platform.contracts.schemas import AnalysisResult, utcnow
from atlas.platform.db.models import (
    AnalysisRow,
    ApiKeyRow,
    PortfolioCompanyInputRow,
    PortfolioRow,
    PortfolioVersionRow,
    ReportRow,
    SnapshotRow,
)
from atlas.platform.runtime.settings import Settings, get_settings

STATIC_DIR = Path(__file__).with_name("static")
# Built React SPA (frontend/ -> `pnpm build`). It is the official browser UI
# and is included in production packages/images. The vanilla UI remains at
# /legacy as a source-checkout fallback and rollback surface.
SPA_DIR = Path(__file__).with_name("spa")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(title="Atlas", version="0.1.0")
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        MaxBodySizeMiddleware,
        max_bytes=resolved_settings.max_request_body_bytes,
    )
    if resolved_settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=resolved_settings.rate_limit_requests_per_minute,
            burst=resolved_settings.rate_limit_burst,
            excluded_paths=("/static", "/assets"),
            trusted_proxy_count=resolved_settings.trusted_proxy_count,
            max_tracked_identities=resolved_settings.rate_limit_max_tracked_identities,
        )
    allowed_origins = [
        origin.strip()
        for origin in resolved_settings.cors_allowed_origins.split(",")
        if origin.strip()
    ]
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.state.container = build_container(resolved_settings)
    app.include_router(_router())
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    spa_assets = SPA_DIR / "assets"
    if spa_assets.exists():
        app.mount("/assets", StaticFiles(directory=spa_assets), name="spa-assets")
    return app


def _container(request: Request) -> Container:
    return request.app.state.container


def _org_id(request: Request) -> str:
    api_key = getattr(request.state, "api_key", None)
    if api_key is None:
        raise RuntimeError("authenticated organization is unavailable")
    return api_key.org_id


def _org_scope(column, org_id: str):
    # NULL is accepted only for legacy rows in the default organization. The
    # migration backfills these values; this branch makes rolling upgrades safe.
    if org_id == DEFAULT_ORG_ID:
        return or_(column == org_id, column.is_(None))
    return column == org_id


def _scoped_row(session: Session, model, row_id: str, org_id: str):
    return session.execute(
        select(model).where(model.id == row_id, _org_scope(model.org_id, org_id))
    ).scalar_one_or_none()


# --- request/response models -------------------------------------------------


class CompanyIn(CompanyFinancialProfile):
    pass


class PortfolioIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    companies: list[CompanyIn] = Field(min_length=1)


class AnalysisIn(BaseModel):
    engine: str = "impairment"
    portfolio_id: str | None = None
    snapshot_id: str | None = None  # default: latest registered snapshot
    params: dict[str, Any] = Field(default_factory=dict)
    # By default an identical request reuses the existing run instead of
    # re-executing the engine; force=True always creates a fresh run.
    force: bool = False


class AgentAskIn(BaseModel):
    question: str
    portfolio_id: str | None = None
    snapshot_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class SessionLoginIn(BaseModel):
    # The key may arrive in the X-API-Key header (preferred) or this body field,
    # so the browser can post it from a login form without exposing it to JS on
    # subsequent requests (the response sets an HttpOnly cookie).
    api_key: str | None = None


COMPANY_FIELDS = tuple(CompanyFinancialProfile.model_fields)


def _portfolio_input_hash(name: str, companies: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        {"name": name, "companies": companies},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _company_row_payload(row: PortfolioCompanyInputRow) -> dict[str, Any]:
    return {field: getattr(row, field) for field in COMPANY_FIELDS}


_ACTIVE_STATUSES = ("queued", "running", "succeeded")
_SEVERITY_ORDER = {"info": 0, "watch": 1, "elevated": 2, "critical": 3}


def _analysis_idempotency_key(
    engine: str,
    engine_version: str,
    model_version: str,
    snapshot_id: str,
    params: dict[str, Any],
) -> str:
    payload = json.dumps(
        {
            "engine": engine,
            "engine_version": engine_version,
            "model_version": model_version,
            "snapshot_id": snapshot_id,
            "params": params,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _resilience_rows(c: Container, run_id: str) -> list[dict[str, Any]]:
    """Parse one run's financial_resilience.csv, or [] if it has none."""
    try:
        path = c.artifacts.open_path(f"{run_id}/financial_resilience.csv")
    except FileNotFoundError:
        return []
    import pandas as pd

    return pd.read_csv(path).to_dict(orient="records")


def _ai_narrative_payload(report: ReportRow) -> dict[str, Any] | None:
    if report.narrative is None:
        return None
    return {
        "narrative": report.narrative,
        "degraded": report.narrative_degraded,
        "reason": report.narrative_reason,
        "model": report.narrative_model,
    }


def _report_narration_question(report: ReportRow) -> str:
    actions = [a.get("title", "") for a in report.content.get("actions", [])]
    action_text = "; ".join(a for a in actions if a) or "no actions were flagged"
    return (
        "Write a short institutional note explaining this decision report. "
        f"Headline: {report.headline} "
        f"Recommended actions: {action_text}. "
        "Explain what the figures imply and why each action was recommended. "
        "Cite every figure with its token and write no other number."
    )


def _previous_succeeded_analysis(
    session: Session,
    row: AnalysisRow,
) -> AnalysisRow | None:
    """The prior succeeded run of the same engine + portfolio, for diffing."""
    stmt = (
        select(AnalysisRow)
        .where(
            AnalysisRow.engine == row.engine,
            AnalysisRow.status == "succeeded",
            AnalysisRow.id != row.id,
            AnalysisRow.created_at < row.created_at,
            _org_scope(AnalysisRow.org_id, row.org_id),
        )
        .order_by(AnalysisRow.created_at.desc())
        .limit(1)
    )
    if row.portfolio_id:
        stmt = stmt.where(AnalysisRow.portfolio_id == row.portfolio_id)
    else:
        stmt = stmt.where(AnalysisRow.portfolio_id.is_(None))
    return session.execute(stmt).scalar_one_or_none()


def _version_companies(session: Session, version_id: str | None) -> list[dict[str, Any]]:
    if not version_id:
        return []
    rows = session.execute(
        select(PortfolioCompanyInputRow)
        .where(PortfolioCompanyInputRow.portfolio_version_id == version_id)
        .order_by(PortfolioCompanyInputRow.position)
    ).scalars()
    return [_company_row_payload(row) for row in rows]


def _current_portfolio_version(
    session: Session,
    portfolio: PortfolioRow,
) -> PortfolioVersionRow | None:
    if not portfolio.current_version_id:
        return None
    return session.get(PortfolioVersionRow, portfolio.current_version_id)


def _portfolio_companies(session: Session, portfolio: PortfolioRow) -> list[dict[str, Any]]:
    companies = _version_companies(session, portfolio.current_version_id)
    return companies or list(portfolio.companies)


def _portfolio_response(session: Session, portfolio: PortfolioRow) -> dict[str, Any]:
    version = _current_portfolio_version(session, portfolio)
    companies = _portfolio_companies(session, portfolio)
    return {
        "portfolio_id": portfolio.id,
        "name": portfolio.name,
        "companies": companies,
        "company_count": len(companies),
        "current_version_id": version.id if version else None,
        "version_number": version.version_number if version else None,
        "created_at": portfolio.created_at,
        "updated_at": portfolio.updated_at or portfolio.created_at,
    }


def _append_portfolio_version(
    session: Session,
    portfolio: PortfolioRow,
    body: PortfolioIn,
) -> tuple[PortfolioVersionRow, bool]:
    companies = [company.model_dump() for company in body.companies]
    input_hash = _portfolio_input_hash(body.name, companies)
    current = _current_portfolio_version(session, portfolio)
    if current and current.input_hash == input_hash:
        return current, False

    latest_number = session.scalar(
        select(func.max(PortfolioVersionRow.version_number)).where(
            PortfolioVersionRow.portfolio_id == portfolio.id
        )
    )
    version = PortfolioVersionRow(
        id=f"pfv_{uuid.uuid4().hex[:12]}",
        portfolio_id=portfolio.id,
        version_number=(latest_number or 0) + 1,
        portfolio_name=body.name,
        input_hash=input_hash,
    )
    session.add(version)
    # The models intentionally avoid ORM relationships. Flush the version header
    # before its company rows so databases that enforce foreign keys (Postgres)
    # never see a child before its parent. SQLite tests do not enforce this by
    # default, which previously hid the ordering defect.
    session.flush()
    for position, company in enumerate(companies):
        session.add(
            PortfolioCompanyInputRow(
                id=f"pfc_{uuid.uuid4().hex[:12]}",
                portfolio_version_id=version.id,
                position=position,
                **company,
            )
        )

    portfolio.name = body.name
    portfolio.companies = companies
    portfolio.current_version_id = version.id
    portfolio.updated_at = utcnow()
    session.flush()
    return version, True


def _router():
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/", include_in_schema=False)
    def frontend():
        spa_index = SPA_DIR / "index.html"
        if spa_index.exists():
            return FileResponse(spa_index, headers={"X-Atlas-Frontend": "react"})
        return FileResponse(
            STATIC_DIR / "index.html",
            headers={"X-Atlas-Frontend": "legacy-fallback"},
        )

    @router.get("/legacy", include_in_schema=False)
    def legacy_frontend():
        return FileResponse(STATIC_DIR / "index.html")

    @router.get("/app", include_in_schema=False)
    @router.get("/app/{path:path}", include_in_schema=False)
    def previous_react_path(path: str = ""):
        return RedirectResponse(url="/", status_code=308)

    @router.post("/auth/session")
    def create_session(request: Request, response: Response, body: SessionLoginIn | None = None):
        """Exchange a valid API key for an HttpOnly session cookie.

        This is the production browser login: the SPA posts a key once, the key
        is verified against the stored hash, and the response sets the same
        cookie the auth dependency already reads. The plaintext key never
        returns to JavaScript, and the cookie is Secure + SameSite=Strict.
        """
        token = request.headers.get("x-api-key") or (body.api_key if body else None)
        if not token:
            raise HTTPException(401, "missing API key")
        c = _container(request)
        with c.session_factory() as session:
            row = session.execute(
                select(ApiKeyRow).where(ApiKeyRow.key_hash == hash_token(token))
            ).scalar_one_or_none()
        if row is None:
            raise HTTPException(401, "invalid API key")

        response.set_cookie(
            key=API_KEY_COOKIE,
            value=token,
            httponly=True,
            secure=c.settings.session_cookie_secure,
            samesite="strict",
            path="/",
        )
        return {
            "authenticated": True,
            "org_id": row.org_id,
            "scopes": row.scopes.split(","),
        }

    @router.delete("/auth/session")
    def delete_session(response: Response):
        """Log out: clear the session cookie."""
        response.delete_cookie(API_KEY_COOKIE, path="/")
        return {"authenticated": False}

    @router.post("/demo/bootstrap", include_in_schema=False)
    def demo_bootstrap(request: Request, response: Response):
        c = _container(request)
        if not c.settings.demo_mode:
            raise HTTPException(404, "local demo mode is not enabled")

        with c.session_factory() as session:
            latest = session.execute(
                select(SnapshotRow).order_by(SnapshotRow.created_at.desc()).limit(1)
            ).scalar_one_or_none()
            if latest is None:
                from atlas.domain.data.synthetic import make_macro_frame

                manifest = c.snapshots.create(
                    {"macro": make_macro_frame()},
                    sources=["synthetic://local-demo"],
                    period_start="2015-01",
                    period_end="2024-12",
                )
                latest = SnapshotRow(
                    snapshot_id=manifest.snapshot_id,
                    manifest=manifest.model_dump(mode="json"),
                )
                session.add(latest)
                session.commit()

            _, token = create_api_key(
                session,
                name="local-browser-session",
                scopes=[SCOPE_READ, SCOPE_RUN],
            )

        response.set_cookie(
            key=API_KEY_COOKIE,
            value=token,
            httponly=True,
            secure=False,
            samesite="strict",
            path="/",
        )

        return {
            "mode": "local-demo",
            "authentication": "http-only-cookie",
            "snapshot_id": latest.snapshot_id,
            "capabilities": sorted(c.registry.capabilities()),
        }

    @router.post("/portfolios", status_code=201, dependencies=[require_scope(SCOPE_RUN)])
    def create_portfolio(body: PortfolioIn, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        row = PortfolioRow(
            id=f"pf_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            name=body.name,
            companies=[co.model_dump() for co in body.companies],
        )
        with c.session_factory() as session:
            session.add(row)
            session.flush()
            _, changed = _append_portfolio_version(session, row, body)
            session.commit()
            response = _portfolio_response(session, row)
        return {**response, "changed": changed}

    @router.get("/portfolios", dependencies=[require_scope(SCOPE_READ)])
    def list_portfolios(
        request: Request,
        limit: int = Query(default=50, ge=1, le=200),
    ):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            rows = session.execute(
                select(PortfolioRow)
                .where(_org_scope(PortfolioRow.org_id, org_id))
                .order_by(func.coalesce(PortfolioRow.updated_at, PortfolioRow.created_at).desc())
                .limit(limit)
            ).scalars()
            portfolios = [_portfolio_response(session, row) for row in rows]
        return {"portfolios": portfolios}

    @router.get(
        "/portfolios/{portfolio_id}/versions",
        dependencies=[require_scope(SCOPE_READ)],
    )
    def list_portfolio_versions(portfolio_id: str, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            portfolio = _scoped_row(session, PortfolioRow, portfolio_id, org_id)
            if portfolio is None:
                raise HTTPException(404, "portfolio not found")
            rows = session.execute(
                select(PortfolioVersionRow)
                .where(PortfolioVersionRow.portfolio_id == portfolio_id)
                .order_by(PortfolioVersionRow.version_number.desc())
            ).scalars()
            versions = [
                {
                    "version_id": row.id,
                    "version_number": row.version_number,
                    "name": row.portfolio_name,
                    "company_count": len(_version_companies(session, row.id)),
                    "input_hash": row.input_hash,
                    "created_at": row.created_at,
                    "is_current": row.id == portfolio.current_version_id,
                }
                for row in rows
            ]
        return {"portfolio_id": portfolio_id, "versions": versions}

    @router.get("/portfolios/{portfolio_id}", dependencies=[require_scope(SCOPE_READ)])
    def get_portfolio(portfolio_id: str, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            row = _scoped_row(session, PortfolioRow, portfolio_id, org_id)
            if row is None:
                raise HTTPException(404, "portfolio not found")
            return _portfolio_response(session, row)

    @router.put("/portfolios/{portfolio_id}", dependencies=[require_scope(SCOPE_RUN)])
    def update_portfolio(portfolio_id: str, body: PortfolioIn, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            row = session.execute(
                select(PortfolioRow)
                .where(PortfolioRow.id == portfolio_id, _org_scope(PortfolioRow.org_id, org_id))
                .with_for_update()
            ).scalar_one_or_none()
            if row is None:
                raise HTTPException(404, "portfolio not found")
            _, changed = _append_portfolio_version(session, row, body)
            session.commit()
            response = _portfolio_response(session, row)
        return {**response, "changed": changed}

    @router.post("/analyses", status_code=202, dependencies=[require_scope(SCOPE_RUN)])
    async def create_analysis(body: AnalysisIn, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            if body.engine not in c.registry.capabilities():
                raise HTTPException(
                    422,
                    f"unknown engine {body.engine!r}; "
                    f"available: {sorted(c.registry.capabilities())}",
                )

            params = dict(body.params)
            portfolio_version_id = None
            if body.portfolio_id:
                portfolio = _scoped_row(session, PortfolioRow, body.portfolio_id, org_id)
                if portfolio is None:
                    raise HTTPException(404, "portfolio not found")
                companies = _portfolio_companies(session, portfolio)
                params["companies"] = companies
                portfolio_version_id = portfolio.current_version_id

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

            worker = c.registry.get(body.engine)
            idempotency_key = _analysis_idempotency_key(
                body.engine,
                worker.engine_version,
                worker.model_version,
                snapshot_id,
                params,
            )

            if not body.force:
                existing = session.execute(
                    select(AnalysisRow)
                    .where(
                        AnalysisRow.idempotency_key == idempotency_key,
                        AnalysisRow.status.in_(_ACTIVE_STATUSES),
                        _org_scope(AnalysisRow.org_id, org_id),
                    )
                    .order_by(AnalysisRow.created_at.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if existing is not None:
                    return {
                        "job_id": existing.id,
                        "status": existing.status,
                        "deduplicated": True,
                    }

            row = AnalysisRow(
                id=f"run_{uuid.uuid4().hex[:12]}",
                org_id=org_id,
                portfolio_id=body.portfolio_id,
                portfolio_version_id=portfolio_version_id,
                engine=body.engine,
                snapshot_id=snapshot_id,
                params=params,
                idempotency_key=idempotency_key,
                status="queued",
            )
            session.add(row)
            session.commit()
            job_id = row.id

        await c.queue.enqueue_analysis(job_id)
        return {"job_id": job_id, "status": "queued", "deduplicated": False}

    @router.get("/analyses", dependencies=[require_scope(SCOPE_READ)])
    def list_analyses(
        request: Request,
        limit: int = Query(default=12, ge=1, le=100),
    ):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            rows = (
                session.execute(
                    select(AnalysisRow)
                    .where(_org_scope(AnalysisRow.org_id, org_id))
                    .order_by(AnalysisRow.created_at.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            portfolio_ids = {row.portfolio_id for row in rows if row.portfolio_id}
            portfolios = (
                session.execute(
                    select(PortfolioRow).where(
                        PortfolioRow.id.in_(portfolio_ids),
                        _org_scope(PortfolioRow.org_id, org_id),
                    )
                )
                .scalars()
                .all()
                if portfolio_ids
                else []
            )
            portfolio_names = {row.id: row.name for row in portfolios}

        analyses = []
        for row in rows:
            metrics = {}
            if row.result:
                metrics = row.result.get("metrics", {})
            regime = None
            if row.engine == "macro_monitor" and metrics:
                regime = max(
                    ("expansion", "tightening", "crisis"),
                    key=lambda name: metrics.get(f"p_regime_{name}", 0.0),
                )
            analyses.append(
                {
                    "job_id": row.id,
                    "portfolio_id": row.portfolio_id,
                    "portfolio_version_id": row.portfolio_version_id,
                    "portfolio_name": portfolio_names.get(row.portfolio_id),
                    "engine": row.engine,
                    "snapshot_id": row.snapshot_id,
                    "status": row.status,
                    "portfolio_mean_p_impairment": metrics.get("portfolio_mean_p_impairment"),
                    "macro_regime": regime,
                    "stress_index": metrics.get("stress_index"),
                    "created_at": row.created_at,
                    "finished_at": row.finished_at,
                }
            )
        return {"analyses": analyses}

    @router.get("/analyses/{analysis_id}", dependencies=[require_scope(SCOPE_READ)])
    def get_analysis(analysis_id: str, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            row = _scoped_row(session, AnalysisRow, analysis_id, org_id)
        if row is None:
            raise HTTPException(404, "analysis not found")
        return {
            "job_id": row.id,
            "portfolio_id": row.portfolio_id,
            "portfolio_version_id": row.portfolio_version_id,
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

    @router.post(
        "/analyses/{analysis_id}/report",
        status_code=201,
        dependencies=[require_scope(SCOPE_RUN)],
    )
    def create_report(analysis_id: str, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            row = _scoped_row(session, AnalysisRow, analysis_id, org_id)
            if row is None:
                raise HTTPException(404, "analysis not found")
            if row.status != "succeeded" or not row.result:
                raise HTTPException(
                    409,
                    f"analysis is {row.status!r}; a report needs a succeeded analysis",
                )

            existing = session.execute(
                select(ReportRow)
                .where(
                    ReportRow.analysis_id == analysis_id,
                    _org_scope(ReportRow.org_id, org_id),
                )
                .order_by(ReportRow.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if existing is not None:
                return {**existing.content, "ai_narrative": _ai_narrative_payload(existing)}

            metrics = dict(row.result.get("metrics", {}))
            previous = _previous_succeeded_analysis(session, row)
            previous_metrics = (
                dict(previous.result.get("metrics", {})) if previous and previous.result else None
            )

            report = build_report(
                run_id=row.id,
                engine=row.engine,
                snapshot_id=row.snapshot_id,
                engine_version=row.result.get("engine_version", ""),
                model_version=row.result.get("model_version", ""),
                metrics=metrics,
                resilience_rows=_resilience_rows(c, row.id),
                previous_metrics=previous_metrics,
                previous_run_id=previous.id if previous else None,
            )

            max_severity = max(
                (a.severity for a in report.actions),
                key=lambda s: _SEVERITY_ORDER[s],
                default="info",
            )
            session.add(
                ReportRow(
                    id=report.report_id,
                    analysis_id=row.id,
                    org_id=row.org_id,
                    engine=row.engine,
                    headline=report.headline,
                    action_count=len(report.actions),
                    max_severity=max_severity,
                    previous_run_id=report.previous_run_id,
                    content=report.model_dump(mode="json"),
                )
            )
            session.commit()
        return report.model_dump(mode="json")

    @router.get(
        "/analyses/{analysis_id}/report",
        dependencies=[require_scope(SCOPE_READ)],
    )
    def get_report(analysis_id: str, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            report = session.execute(
                select(ReportRow)
                .where(
                    ReportRow.analysis_id == analysis_id,
                    _org_scope(ReportRow.org_id, org_id),
                )
                .order_by(ReportRow.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if report is None:
                raise HTTPException(404, "no report for this analysis")
            return {**report.content, "ai_narrative": _ai_narrative_payload(report)}

    @router.post(
        "/analyses/{analysis_id}/report/narrative",
        dependencies=[require_scope(SCOPE_RUN)],
    )
    def narrate_report(analysis_id: str, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            report = session.execute(
                select(ReportRow)
                .where(
                    ReportRow.analysis_id == analysis_id,
                    _org_scope(ReportRow.org_id, org_id),
                )
                .order_by(ReportRow.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if report is None:
                raise HTTPException(404, "build a report before narrating it")
            analysis = _scoped_row(session, AnalysisRow, analysis_id, org_id)
            if analysis is None or not analysis.result:
                raise HTTPException(409, "analysis result is unavailable")

            result = AnalysisResult.model_validate(analysis.result)
            question = _report_narration_question(report)
            narrative, _citations, degraded, reason, _usage = c.agent.narrate(question, [result])

            report.narrative = narrative
            report.narrative_degraded = degraded
            report.narrative_reason = reason
            report.narrative_model = c.agent.llm.model
            session.commit()
            payload = _ai_narrative_payload(report)
        return payload

    @router.get("/reports", dependencies=[require_scope(SCOPE_READ)])
    def list_reports(
        request: Request,
        limit: int = Query(default=10, ge=1, le=100),
    ):
        c = _container(request)
        org_id = _org_id(request)
        with c.session_factory() as session:
            rows = (
                session.execute(
                    select(ReportRow)
                    .where(_org_scope(ReportRow.org_id, org_id))
                    .order_by(ReportRow.created_at.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            analysis_ids = {row.analysis_id for row in rows}
            analyses = (
                session.execute(
                    select(AnalysisRow).where(
                        AnalysisRow.id.in_(analysis_ids),
                        _org_scope(AnalysisRow.org_id, org_id),
                    )
                )
                .scalars()
                .all()
                if analysis_ids
                else []
            )
            portfolio_by_analysis = {a.id: a.portfolio_id for a in analyses}
            portfolio_ids = {pid for pid in portfolio_by_analysis.values() if pid}
            portfolios = (
                session.execute(
                    select(PortfolioRow).where(
                        PortfolioRow.id.in_(portfolio_ids),
                        _org_scope(PortfolioRow.org_id, org_id),
                    )
                )
                .scalars()
                .all()
                if portfolio_ids
                else []
            )
            portfolio_names = {p.id: p.name for p in portfolios}

            reports = [
                {
                    "report_id": row.id,
                    "analysis_id": row.analysis_id,
                    "engine": row.engine,
                    "headline": row.headline,
                    "action_count": row.action_count,
                    "max_severity": row.max_severity,
                    "portfolio_id": portfolio_by_analysis.get(row.analysis_id),
                    "portfolio_name": portfolio_names.get(
                        portfolio_by_analysis.get(row.analysis_id)
                    ),
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        return {"reports": reports}

    @router.post("/agent/ask", dependencies=[require_scope(SCOPE_RUN)])
    def agent_ask(body: AgentAskIn, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        params = dict(body.params)
        portfolio_context = ""

        with c.session_factory() as session:
            if body.portfolio_id:
                portfolio = _scoped_row(session, PortfolioRow, body.portfolio_id, org_id)
                if portfolio is None:
                    raise HTTPException(404, "portfolio not found")
                companies = _portfolio_companies(session, portfolio)
                params["companies"] = companies
                names = [co.get("name", "?") for co in companies]
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
            org_id=org_id,
        )
        return answer.model_dump(mode="json")

    @router.get("/agent/traces/{trace_id}", dependencies=[require_scope(SCOPE_READ)])
    def get_trace(trace_id: str, request: Request):
        c = _container(request)
        org_id = _org_id(request)
        row = c.agent.trace_store.get(trace_id, org_id)
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
        org_id = _org_id(request)
        with c.session_factory() as session:
            if _scoped_row(session, AnalysisRow, run_id, org_id) is None:
                raise HTTPException(404, "artifact not found")
        try:
            path = c.artifacts.open_path(f"{run_id}/{name}")
        except FileNotFoundError:
            raise HTTPException(404, "artifact not found") from None
        return FileResponse(path, filename=name)

    @router.get("/health")
    def health(request: Request, deep: bool = Query(default=False)):
        # The default probe checks only the core dependencies (database, queue)
        # and must stay cheap: platform health checks hit it constantly. The
        # live FRED check is an outbound call, so it runs only on ?deep=true —
        # otherwise every probe would amplify traffic to FRED and inherit its
        # latency. FRED is informational anyway: an outage degrades ingestion,
        # not the API, which runs on the last frozen snapshot.
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

        if deep:
            try:
                import httpx

                from atlas.domain.data.fred import FREDGRAPH_URL

                resp = httpx.head(FREDGRAPH_URL, params={"id": "FEDFUNDS"}, timeout=3.0)
                checks["fred"] = "ok" if resp.status_code < 500 else f"error: {resp.status_code}"
            except Exception as exc:
                checks["fred"] = f"error: {type(exc).__name__}"

        core = (checks["database"], checks["queue"])
        status = "ok" if all(not v.startswith("error") for v in core) else "degraded"
        return {"status": status, "checks": checks}

    return router


# uvicorn entrypoint: uvicorn atlas.interfaces.api.app:create_app --factory
