from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import uuid

from shared.contracts.broker import AccountInfo, BrokerResponse, Candle, SymbolInfo, Tick
from trading.connectors.base import BrokerConnector


class SimulationAdapter(BrokerConnector):
    """Deterministic, clearly simulated broker for Linux development and tests."""

    SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD")

    def __init__(self) -> None:
        self._connected = False
        self._account = AccountInfo(
            account_id="SIM-DEMO-001",
            broker="Simulation",
            environment="simulation",
            currency="USD",
            balance=Decimal("10000"),
            equity=Decimal("10000"),
            margin=Decimal("0"),
            free_margin=Decimal("10000"),
            margin_level=None,
            simulated=True,
        )
        self._submitted: dict[str, BrokerResponse] = {}

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def connection_status(self) -> dict:
        return {"connected": self._connected, "environment": "simulation", "simulated": True}

    def get_account_info(self) -> AccountInfo:
        self._require_connection()
        return self._account

    def get_instruments(self) -> list[SymbolInfo]:
        self._require_connection()
        return [self.get_symbol_info(symbol) for symbol in self.SYMBOLS]

    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        self._require_connection()
        if symbol not in self.SYMBOLS:
            raise KeyError(f"Unknown simulated symbol: {symbol}")
        digits = 2 if symbol == "XAUUSD" else (3 if symbol.endswith("JPY") else 5)
        tick_size = Decimal("0.01") if digits == 2 else Decimal(1).scaleb(-digits)
        return SymbolInfo(
            symbol=symbol,
            description=f"{symbol} simulated instrument",
            contract_size=Decimal("100000"),
            tick_size=tick_size,
            tick_value=Decimal("1"),
            minimum_volume=Decimal("0.01"),
            maximum_volume=Decimal("100"),
            volume_step=Decimal("0.01"),
            digits=digits,
            trade_allowed=True,
        )

    def get_tick(self, symbol: str) -> Tick:
        self._require_connection()
        info = self.get_symbol_info(symbol)
        seed = int(hashlib.sha256(f"{symbol}:{datetime.now(UTC).replace(microsecond=0)}".encode()).hexdigest()[:8], 16)
        base = Decimal("1950") if symbol == "XAUUSD" else Decimal("100") if symbol.endswith("JPY") else Decimal("1.10000")
        offset = Decimal(seed % 10000).scaleb(-info.digits)
        bid = (base + offset).quantize(tick_size := info.tick_size)
        ask = (bid + tick_size * 10).quantize(tick_size)
        return Tick(symbol=symbol, bid=bid, ask=ask, time=datetime.now(UTC))

    def get_historical_candles(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> list[Candle]:
        self._require_connection()
        info = self.get_symbol_info(symbol)
        minutes = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}.get(timeframe)
        if minutes is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        candles: list[Candle] = []
        current = start
        index = 0
        base = Decimal("1950") if symbol == "XAUUSD" else Decimal("100") if symbol.endswith("JPY") else Decimal("1.10000")
        while current <= end:
            drift = Decimal((index % 20) - 10).scaleb(-info.digits)
            close = (base + drift).quantize(info.tick_size)
            open_price = (close - Decimal("0.00002") if info.digits == 5 else close - info.tick_size).quantize(info.tick_size)
            high = max(open_price, close) + info.tick_size
            low = min(open_price, close) - info.tick_size
            candles.append(Candle(symbol, timeframe, current, open_price, high, low, close, Decimal("100")))
            current += timedelta(minutes=minutes)
            index += 1
        return candles

    def get_open_positions(self) -> list[dict]:
        self._require_connection()
        return []

    def get_pending_orders(self) -> list[dict]:
        self._require_connection()
        return []

    def submit_order(self, symbol: str, direction: str, volume, stop_loss=None, take_profit=None, idempotency_key: str | None = None) -> BrokerResponse:
        self._require_connection()
        if stop_loss is None:
            raise ValueError("Protected simulated orders require a stop loss")
        key = idempotency_key or str(uuid.uuid4())
        if key in self._submitted:
            previous = self._submitted[key]
            return BrokerResponse(True, previous.broker_order_id, previous.broker_position_id, "IDEMPOTENT_RETURN", "Existing simulated order returned", True)
        broker_id = f"SIM-{uuid.uuid4()}"
        response = BrokerResponse(True, broker_id, broker_id, "filled", "Simulated execution accepted", True)
        self._submitted[key] = response
        return response

    def _require_connection(self) -> None:
        if not self._connected:
            raise ConnectionError("Simulation broker is disconnected")
