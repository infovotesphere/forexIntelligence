"""add user display names

Revision ID: 20261124_004
Revises: 20261123_003
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261124_004"
down_revision: Union[str, None] = "20261123_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "display_name")
