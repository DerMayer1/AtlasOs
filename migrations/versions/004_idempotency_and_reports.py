"""analysis idempotency key and decision reports

Revision ID: 004
Revises: 003
Create Date: 2026-06-15
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("idempotency_key", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_analyses_idempotency_key",
        "analyses",
        ["idempotency_key"],
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.String(64),
            sa.ForeignKey("analyses.id"),
            nullable=False,
        ),
        sa.Column("org_id", sa.String(64), nullable=True),
        sa.Column("engine", sa.String(100), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("action_count", sa.Integer(), nullable=False),
        sa.Column("max_severity", sa.String(20), nullable=False),
        sa.Column("previous_run_id", sa.String(64), nullable=True),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_analysis_id", "reports", ["analysis_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_analysis_id", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_analyses_idempotency_key", table_name="analyses")
    op.drop_column("analyses", "idempotency_key")
