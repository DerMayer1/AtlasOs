"""initial schema: portfolios, analyses, snapshots, api_keys

Revision ID: 001
Revises:
Create Date: 2026-06-11
"""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("org_id", sa.String(64), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("companies", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("org_id", sa.String(64), nullable=True),
        sa.Column("portfolio_id", sa.String(64), nullable=True),
        sa.Column("engine", sa.String(100), nullable=False),
        sa.Column("snapshot_id", sa.String(100), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_analyses_status", "analyses", ["status"])
    op.create_index("ix_analyses_portfolio", "analyses", ["portfolio_id"])
    op.create_table(
        "snapshots",
        sa.Column("snapshot_id", sa.String(100), primary_key=True),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("org_id", sa.String(64), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("scopes", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("snapshots")
    op.drop_index("ix_analyses_portfolio", table_name="analyses")
    op.drop_index("ix_analyses_status", table_name="analyses")
    op.drop_table("analyses")
    op.drop_table("portfolios")
