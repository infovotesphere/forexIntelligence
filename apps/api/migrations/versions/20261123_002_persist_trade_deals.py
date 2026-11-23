"""persist MT5 broker deal history

Revision ID: 20261123_002
Revises: 20261123_001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20261123_002"
down_revision: Union[str, None] = "20261123_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trade_deals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("server", sa.String(length=255), nullable=False),
        sa.Column("environment", sa.String(length=8), nullable=False),
        sa.Column("ticket", sa.String(length=64), nullable=False),
        sa.Column("order_ticket", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("volume", sa.Numeric(precision=30, scale=12), nullable=False),
        sa.Column("price", sa.Numeric(precision=30, scale=12), nullable=False),
        sa.Column("profit", sa.Numeric(precision=30, scale=12), nullable=False),
        sa.Column("commission", sa.Numeric(precision=30, scale=12), nullable=False),
        sa.Column("swap", sa.Numeric(precision=30, scale=12), nullable=False),
        sa.Column("deal_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("simulated", sa.Boolean(), nullable=False),
        sa.UniqueConstraint(
            "account_id",
            "server",
            "environment",
            "ticket",
            name="uq_trade_deals_broker_ticket",
        ),
    )
    op.create_index(
        "ix_trade_deals_account_time",
        "trade_deals",
        ["account_id", "server", "environment", "deal_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_trade_deals_account_time", table_name="trade_deals")
    op.drop_table("trade_deals")
