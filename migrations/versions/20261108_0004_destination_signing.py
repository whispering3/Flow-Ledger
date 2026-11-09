"""destination signing secrets

Revision ID: 20261108_0004
Revises: 20261108_0003
Create Date: 2026-11-08 00:30:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261108_0004"
down_revision = "20261108_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destinations",
        sa.Column("signing_secret_ciphertext", sa.String(length=512), nullable=True),
    )
    op.execute("UPDATE destinations SET enabled = false WHERE signing_secret_ciphertext IS NULL")


def downgrade() -> None:
    op.drop_column("destinations", "signing_secret_ciphertext")
