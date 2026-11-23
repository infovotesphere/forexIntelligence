from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class AccountInfo:
    account_id: str
    broker: str
    environment: str
    currency: str
    balance: Decimal
    equity: Decimal
    margin: Decimal
    free_margin: Decimal
    margin_level: Decimal | None
    simulated: bool


@dataclass(frozen=True)
class Tick:
    symbol: str
    bid: Decimal
    ask: Decimal
    time: datetime


@dataclass(frozen=True)
class Candle:
    symbol: str
    timeframe: str
    time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str
    description: str
    contract_size: Decimal
    tick_size: Decimal
    tick_value: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    digits: int
    trade_allowed: bool


@dataclass(frozen=True)
class BrokerResponse:
    accepted: bool
    broker_order_id: str | None
    broker_position_id: str | None
    status: str
    message: str
    simulated: bool
