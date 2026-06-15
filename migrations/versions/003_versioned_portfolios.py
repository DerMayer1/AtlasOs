"""versioned portfolios and normalized company inputs

Revision ID: 003
Revises: 002
Create Date: 2026-06-15
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portfolios",
        sa.Column("current_version_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "portfolios",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "portfolio_versions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "portfolio_id",
            sa.String(64),
            sa.ForeignKey("portfolios.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("portfolio_name", sa.String(200), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "portfolio_id",
            "version_number",
            name="uq_portfolio_versions_portfolio_number",
        ),
    )
    op.create_index(
        "ix_portfolio_versions_portfolio_id",
        "portfolio_versions",
        ["portfolio_id"],
    )
    op.create_table(
        "portfolio_company_inputs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "portfolio_version_id",
            sa.String(64),
            sa.ForeignKey("portfolio_versions.id"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sector", sa.String(100), nullable=False),
        sa.Column("geography", sa.String(100), nullable=False),
        sa.Column("ebitda", sa.Float(), nullable=False),
        sa.Column("multiple", sa.Float(), nullable=False),
        sa.Column("carrying_value", sa.Float(), nullable=False),
        sa.Column("ebitda_margin", sa.Float(), nullable=True),
        sa.Column("ebitda_volatility", sa.Float(), nullable=False),
        sa.Column("macro_sensitivity", sa.Float(), nullable=False),
        sa.Column("sector_sensitivity", sa.Float(), nullable=False),
        sa.Column("multiple_volatility", sa.Float(), nullable=False),
        sa.Column("multiple_floor", sa.Float(), nullable=True),
        sa.Column("multiple_ceiling", sa.Float(), nullable=True),
        sa.Column("debt", sa.Float(), nullable=False),
        sa.Column("cash", sa.Float(), nullable=False),
        sa.Column("annual_interest_expense", sa.Float(), nullable=True),
        sa.Column("interest_rate", sa.Float(), nullable=False),
        sa.Column("debt_due_1y", sa.Float(), nullable=False),
        sa.UniqueConstraint(
            "portfolio_version_id",
            "position",
            name="uq_portfolio_company_inputs_version_position",
        ),
    )
    op.create_index(
        "ix_portfolio_company_inputs_portfolio_version_id",
        "portfolio_company_inputs",
        ["portfolio_version_id"],
    )
    op.add_column(
        "analyses",
        sa.Column(
            "portfolio_version_id",
            sa.String(64),
            sa.ForeignKey("portfolio_versions.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_analyses_portfolio_version_id",
        "analyses",
        ["portfolio_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_analyses_portfolio_version_id", table_name="analyses")
    op.drop_column("analyses", "portfolio_version_id")
    op.drop_index(
        "ix_portfolio_company_inputs_portfolio_version_id",
        table_name="portfolio_company_inputs",
    )
    op.drop_table("portfolio_company_inputs")
    op.drop_index("ix_portfolio_versions_portfolio_id", table_name="portfolio_versions")
    op.drop_table("portfolio_versions")
    op.drop_column("portfolios", "updated_at")
    op.drop_column("portfolios", "current_version_id")
