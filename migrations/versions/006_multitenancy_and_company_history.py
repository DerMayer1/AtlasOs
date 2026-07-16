"""organization isolation and company EBITDA histories

Revision ID: 006
Revises: 005
Create Date: 2026-07-15
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None

DEFAULT_ORG_ID = "org_default"
ORG_TABLES = ("portfolios", "analyses", "reports", "agent_traces", "api_keys")


def upgrade() -> None:
    organizations = op.create_table(
        "organizations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    op.bulk_insert(
        organizations,
        [
            {
                "id": DEFAULT_ORG_ID,
                "slug": "default",
                "name": "Default organization",
                "created_at": datetime.now(UTC),
            }
        ],
    )

    for table in ORG_TABLES:
        op.execute(
            sa.text(f"UPDATE {table} SET org_id = :org_id WHERE org_id IS NULL").bindparams(
                org_id=DEFAULT_ORG_ID
            )
        )
        with op.batch_alter_table(table) as batch:
            batch.alter_column("org_id", existing_type=sa.String(64), nullable=False)
            batch.create_index(f"ix_{table}_org_id", ["org_id"])

    with op.batch_alter_table("portfolio_company_inputs") as batch:
        batch.add_column(
            sa.Column("ebitda_history", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )
        batch.alter_column("ebitda_volatility", existing_type=sa.Float(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("portfolio_company_inputs") as batch:
        batch.alter_column("ebitda_volatility", existing_type=sa.Float(), nullable=False)
        batch.drop_column("ebitda_history")
    for table in reversed(ORG_TABLES):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_org_id")
            batch.alter_column("org_id", existing_type=sa.String(64), nullable=True)
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
