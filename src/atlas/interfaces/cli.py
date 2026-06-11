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
                {"name": "Alpha Industrials", "ebitda": 120.0, "multiple": 8.0,
                 "carrying_value": 900.0},
                {"name": "Beta Logistics", "ebitda": 60.0, "multiple": 6.5,
                 "carrying_value": 450.0},
                {"name": "Gamma Health", "ebitda": 200.0, "multiple": 11.0,
                 "carrying_value": 2400.0},
            ],
        )
        session.add(portfolio)
        session.commit()
        _, token = create_api_key(session, name="demo", scopes=["read", "run"])

    print(f"snapshot_id : {manifest.snapshot_id}")
    print(f"portfolio_id: {portfolio.id}")
    print(f"api_key     : {token}   (shown once — store it now)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atlas")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db")
    sub.add_parser("seed")
    args = parser.parse_args(argv)

    if args.command == "init-db":
        cmd_init_db()
    elif args.command == "seed":
        cmd_seed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
