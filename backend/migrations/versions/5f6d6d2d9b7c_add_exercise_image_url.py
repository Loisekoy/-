"""add exercise image url

Revision ID: 5f6d6d2d9b7c
Revises: 8da40fe7d247
Create Date: 2026-09-16 12:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5f6d6d2d9b7c"
down_revision: str | Sequence[str] | None = "8da40fe7d247"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("exercises", sa.Column("image_url", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("exercises", "image_url")
