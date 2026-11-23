from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class TradeDeal(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "trade_deals"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "server",
            "environment",
            "ticket",
            name="uq_trade_deals_broker_ticket",
        ),
        Index(
            "ix_trade_deals_account_time",
            "account_id",
            "server",
            "environment",
            "deal_time",
        ),
    )

    account_id: Mapped[str] = mapped_column(String(64), nullable=False)
    server: Mapped[str] = mapped_column(String(255), nullable=False)
    environment: Mapped[str] = mapped_column(String(8), nullable=False)
    ticket: Mapped[str] = mapped_column(String(64), nullable=False)
    order_ticket: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    profit: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    commission: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    swap: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    deal_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
