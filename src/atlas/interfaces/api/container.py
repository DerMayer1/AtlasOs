"""Wires settings into concrete services. Held on app.state; tests build their
own container against SQLite + in-process queue."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from atlas.agent.llm import AnthropicLLMClient, LLMClient, NullLLMClient
from atlas.agent.service import AgentService
from atlas.agent.trace_store import TraceStore
from atlas.domain.engines import build_registry
from atlas.platform.audit.artifacts import ArtifactStore
from atlas.platform.audit.snapshots import SnapshotStore
from atlas.platform.db.models import Base
from atlas.platform.db.session import make_engine, make_session_factory
from atlas.platform.runtime.queue import ArqQueue, InProcessQueue, JobQueue
from atlas.platform.runtime.registry import EngineRegistry
from atlas.platform.runtime.runner import execute_analysis
from atlas.platform.runtime.settings import Settings


@dataclass
class Container:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    registry: EngineRegistry
    snapshots: SnapshotStore
    artifacts: ArtifactStore
    queue: JobQueue
    agent: AgentService


def build_container(settings: Settings) -> Container:
    engine = make_engine(settings.database_url)
    if settings.auto_create_schema and settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)

    session_factory = make_session_factory(engine)
    registry = build_registry()
    snapshots = SnapshotStore(settings.data_dir / "snapshots")
    artifacts = ArtifactStore(settings.data_dir / "artifacts")

    queue: JobQueue
    if settings.redis_url:
        queue = ArqQueue(settings.redis_url)
    else:
        queue = InProcessQueue(
            lambda analysis_id: execute_analysis(
                analysis_id, session_factory, registry, snapshots, artifacts
            )
        )

    llm: LLMClient = (
        AnthropicLLMClient(settings.anthropic_api_key, settings.llm_model)
        if settings.anthropic_api_key
        else NullLLMClient()
    )
    agent = AgentService(
        registry=registry,
        snapshots=snapshots,
        artifacts=artifacts,
        session_factory=session_factory,
        trace_store=TraceStore(session_factory),
        llm=llm,
    )

    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        registry=registry,
        snapshots=snapshots,
        artifacts=artifacts,
        queue=queue,
        agent=agent,
    )
