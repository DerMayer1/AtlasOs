"""agent_traces table (PRD R7)

Revision ID: 002
Revises: 001
Create Date: 2026-06-11
"""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_traces",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("org_id", sa.String(64), nullable=True),
        sa.Column("portfolio_id", sa.String(64), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("executed", sa.JSON(), nullable=False),
        sa.Column("run_ids", sa.JSON(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("citations_valid", sa.Boolean(), nullable=False),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("degraded_reason", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.String(100), nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_traces_portfolio", "agent_traces", ["portfolio_id"])
    op.create_index("ix_agent_traces_created", "agent_traces", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_traces_created", table_name="agent_traces")
    op.drop_index("ix_agent_traces_portfolio", table_name="agent_traces")
    op.drop_table("agent_traces")
