"""optional AI narrative annotation on decision reports

Revision ID: 005
Revises: 004
Create Date: 2026-06-15
"""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("narrative", sa.Text(), nullable=True))
    op.add_column(
        "reports",
        sa.Column("narrative_degraded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("reports", sa.Column("narrative_reason", sa.Text(), nullable=True))
    op.add_column("reports", sa.Column("narrative_model", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "narrative_model")
    op.drop_column("reports", "narrative_reason")
    op.drop_column("reports", "narrative_degraded")
    op.drop_column("reports", "narrative")
