from abc import ABC, abstractmethod
from datetime import datetime

from shared.contracts.broker import AccountInfo, BrokerResponse, Candle, SymbolInfo, Tick


class BrokerConnector(ABC):
    @abstractmethod
    def connect(self) -> bool:
        """Establish broker connectivity."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect broker connectivity."""

    @abstractmethod
    def connection_status(self) -> dict:
        """Return a structured connection state."""

    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        ...

    @abstractmethod
    def get_instruments(self) -> list[SymbolInfo]:
        ...

    @abstractmethod
    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        ...

    @abstractmethod
    def get_tick(self, symbol: str) -> Tick:
        ...

    @abstractmethod
    def get_historical_candles(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> list[Candle]:
        ...

    @abstractmethod
    def get_open_positions(self) -> list[dict]:
        ...

    @abstractmethod
    def get_pending_orders(self) -> list[dict]:
        ...

    @abstractmethod
    def submit_order(self, symbol: str, direction: str, volume, stop_loss=None, take_profit=None, idempotency_key: str | None = None) -> BrokerResponse:
        ...
