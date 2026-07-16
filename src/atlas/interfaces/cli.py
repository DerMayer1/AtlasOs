"""Operational CLI.

python -m atlas.interfaces.cli init-db   # create schema (Alembic upgrade head)
python -m atlas.interfaces.cli seed      # demo snapshot + portfolio + API key
"""

from __future__ import annotations

import argparse
import sys
import uuid

from atlas.platform.runtime.settings import get_settings


def cmd_init_db() -> None:
    from alembic import command
    from alembic.config import Config

    config = Config("alembic.ini")
    command.upgrade(config, "head")
    print("schema is up to date")


def cmd_seed() -> None:
    from atlas.domain.data.synthetic import make_macro_frame
    from atlas.interfaces.api.auth import create_api_key
    from atlas.platform.audit.snapshots import SnapshotStore
    from atlas.platform.db.models import Base, PortfolioRow, SnapshotRow
    from atlas.platform.db.session import make_engine, make_session_factory

    settings = get_settings()
    engine = make_engine(settings.database_url)
    if settings.auto_create_schema and settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)

    snapshots = SnapshotStore(settings.data_dir / "snapshots")
    manifest = snapshots.create(
        {"macro": make_macro_frame()},
        sources=["synthetic://demo"],
        period_start="2015-01",
        period_end="2024-12",
    )

    with session_factory() as session:
        if session.get(SnapshotRow, manifest.snapshot_id) is None:
            session.add(
                SnapshotRow(
                    snapshot_id=manifest.snapshot_id,
                    manifest=manifest.model_dump(mode="json"),
                )
            )
        portfolio = PortfolioRow(
            id=f"pf_{uuid.uuid4().hex[:12]}",
            name="Demo Portfolio",
            companies=[
                {
                    "name": "Alpha Industrials",
                    "sector": "industrials",
                    "ebitda": 120.0,
                    "multiple": 8.0,
                    "carrying_value": 900.0,
                    "debt": 420.0,
                    "cash": 90.0,
                    "debt_due_1y": 80.0,
                },
                {
                    "name": "Beta Logistics",
                    "sector": "logistics",
                    "ebitda": 60.0,
                    "multiple": 6.5,
                    "carrying_value": 450.0,
                    "ebitda_volatility": 0.38,
                    "debt": 310.0,
                    "cash": 35.0,
                    "debt_due_1y": 95.0,
                },
                {
                    "name": "Gamma Health",
                    "sector": "healthcare",
                    "ebitda": 200.0,
                    "multiple": 11.0,
                    "carrying_value": 2400.0,
                    "ebitda_volatility": 0.22,
                    "macro_sensitivity": 0.75,
                    "debt": 650.0,
                    "cash": 180.0,
                    "debt_due_1y": 70.0,
                },
            ],
        )
        session.add(portfolio)
        session.commit()
        _, token = create_api_key(session, name="demo", scopes=["read", "run"])

    print(f"snapshot_id : {manifest.snapshot_id}")
    print(f"portfolio_id: {portfolio.id}")
    print(f"api_key     : {token}   (shown once — store it now)")


def cmd_ingest() -> None:
    """Fetch FRED data and freeze it as a snapshot (PRD R4 + R2)."""
    from atlas.domain.data.fred import FredClient, build_macro_frame
    from atlas.platform.audit.snapshots import SnapshotStore
    from atlas.platform.db.models import Base, SnapshotRow
    from atlas.platform.db.session import make_engine, make_session_factory

    settings = get_settings()
    client = FredClient(settings.data_dir / "cache" / "fred")
    macro = build_macro_frame(client)

    snapshots = SnapshotStore(settings.data_dir / "snapshots")
    manifest = snapshots.create(
        {"macro": macro},
        sources=["fredgraph:fed_funds,baa_aaa_spread,t10y2y,cpi_yoy,unemployment"],
        period_start=str(macro.index.min().date()),
        period_end=str(macro.index.max().date()),
    )

    engine = make_engine(settings.database_url)
    if settings.auto_create_schema and settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    with make_session_factory(engine)() as session:
        if session.get(SnapshotRow, manifest.snapshot_id) is None:
            session.add(
                SnapshotRow(
                    snapshot_id=manifest.snapshot_id,
                    manifest=manifest.model_dump(mode="json"),
                )
            )
            session.commit()
    print(f"snapshot_id : {manifest.snapshot_id}")
    print(f"period      : {manifest.period_start} -> {manifest.period_end}")
    print(f"rows        : {manifest.tables[0].rows}")


def cmd_demo(port: int) -> None:
    """Run the complete local product flow with explicit demo bootstrap."""
    import uvicorn

    from atlas.interfaces.api.app import create_app

    settings = get_settings().model_copy(update={"demo_mode": True})
    uvicorn.run(create_app(settings), host="127.0.0.1", port=port)


def _session_factory():
    from atlas.platform.db.models import Base
    from atlas.platform.db.session import make_engine, make_session_factory

    settings = get_settings()
    engine = make_engine(settings.database_url)
    if settings.auto_create_schema and settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    return make_session_factory(engine)


def cmd_create_org(name: str, slug: str) -> None:
    from atlas.interfaces.api.auth import ensure_organization

    org_id = f"org_{uuid.uuid4().hex[:12]}"
    with _session_factory()() as session:
        ensure_organization(session, org_id, name=name, slug=slug)
        session.commit()
    print(f"org_id: {org_id}")


def cmd_create_key(org_id: str, name: str, scopes: str) -> None:
    from atlas.interfaces.api.auth import create_api_key
    from atlas.platform.db.models import OrganizationRow

    parsed = [scope.strip() for scope in scopes.split(",") if scope.strip()]
    if not parsed or not set(parsed) <= {"read", "run"}:
        raise SystemExit("scopes must be a comma-separated subset of read,run")
    with _session_factory()() as session:
        if session.get(OrganizationRow, org_id) is None:
            raise SystemExit(f"organization {org_id!r} does not exist")
        _, token = create_api_key(session, name=name, scopes=parsed, org_id=org_id)
    print(f"api_key: {token}   (shown once - store it now)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atlas")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db")
    sub.add_parser("seed")
    sub.add_parser("ingest")
    demo = sub.add_parser("demo")
    demo.add_argument("--port", type=int, default=8000)
    create_org = sub.add_parser("create-org")
    create_org.add_argument("--name", required=True)
    create_org.add_argument("--slug", required=True)
    create_key = sub.add_parser("create-key")
    create_key.add_argument("--org-id", required=True)
    create_key.add_argument("--name", required=True)
    create_key.add_argument("--scopes", default="read,run")
    args = parser.parse_args(argv)

    if args.command == "init-db":
        cmd_init_db()
    elif args.command == "seed":
        cmd_seed()
    elif args.command == "ingest":
        cmd_ingest()
    elif args.command == "demo":
        cmd_demo(args.port)
    elif args.command == "create-org":
        cmd_create_org(args.name, args.slug)
    elif args.command == "create-key":
        cmd_create_key(args.org_id, args.name, args.scopes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
