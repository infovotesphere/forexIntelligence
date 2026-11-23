"""persist validated trading signals

Revision ID: 20261123_003
Revises: 20261123_002
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20261123_003"
down_revision: Union[str, None] = "20261123_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trading_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("signal_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("strategy", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("simulated", sa.Boolean(), nullable=False),
        sa.Column("data_source", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("signal_id", name="uq_trading_signals_signal_id"),
    )
    op.create_index("ix_trading_signals_created", "trading_signals", ["created_at"])
    op.create_index("ix_trading_signals_symbol_status", "trading_signals", ["symbol", "status"])


def downgrade() -> None:
    op.drop_index("ix_trading_signals_symbol_status", table_name="trading_signals")
    op.drop_index("ix_trading_signals_created", table_name="trading_signals")
    op.drop_table("trading_signals")
