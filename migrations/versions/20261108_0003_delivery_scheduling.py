"""delivery scheduling state

Revision ID: 20261108_0003
Revises: 20261108_0002
Create Date: 2026-11-08 00:20:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261108_0003"
down_revision = "20261108_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("executions", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("executions", "started_at")
