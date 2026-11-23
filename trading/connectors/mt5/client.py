import sys
from datetime import UTC, datetime
from decimal import Decimal

from shared.contracts.broker import AccountInfo, Candle, SymbolInfo, Tick
from trading.connectors.base import BrokerConnector


class MT5Adapter(BrokerConnector):
    """Windows MT5 read adapter; broker-side order submission is deliberately disabled."""

    TIMEFRAMES = ("M5", "M15", "M30", "H1", "H4", "D1")

    def __init__(self, login: int, password: str, server: str, environment: str = "demo") -> None:
        if sys.platform != "win32":
            raise RuntimeError("MT5Adapter is available only on Windows")
        if environment not in {"demo", "live"}:
            raise ValueError("MT5 environment must be demo or live")
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise RuntimeError("Install apps/api/requirements-windows.txt on the Windows MT5 worker") from exc
        self._mt5 = mt5
        self._login = login
        self._password = password
        self._server = server
        self._environment = environment

    def connect(self) -> bool:
        self.disconnect()
        if not self._mt5.initialize(login=self._login, password=self._password, server=self._server):
            return False
        account = self._mt5.account_info()
        expected_mode = self._expected_trade_mode()
        if account is None or int(account.trade_mode) != expected_mode:
            self.disconnect()
            raise PermissionError(f"The MT5 account is not a {self._environment} account")
        if int(account.login) != self._login or account.server != self._server:
            self.disconnect()
            raise PermissionError("MT5 account login or server does not match the requested account")
        return True

    def disconnect(self) -> None:
        self._mt5.shutdown()

    def last_error(self):
        return self._mt5.last_error()

    def connection_status(self) -> dict:
        terminal = self._mt5.terminal_info()
        account = self._mt5.account_info()
        connected = (
            terminal is not None
            and account is not None
            and int(account.trade_mode) == self._expected_trade_mode()
            and int(account.login) == self._login
            and account.server == self._server
        )
        return {
            "connected": connected,
            "environment": self._environment if connected else "disconnected",
            "simulated": False,
            "broker": "MetaTrader 5",
        }

    def get_account_info(self) -> AccountInfo:
        self._require_readonly_connection()
        account = self._mt5.account_info()
        return AccountInfo(
            account_id=str(account.login),
            broker="MetaTrader 5",
            environment=self._environment,
            currency=account.currency,
            balance=Decimal(str(account.balance)),
            equity=Decimal(str(account.equity)),
            margin=Decimal(str(account.margin)),
            free_margin=Decimal(str(account.margin_free)),
            margin_level=Decimal(str(account.margin_level)) if account.margin_level else None,
            simulated=False,
        )

    def get_instruments(self) -> list[SymbolInfo]:
        self._require_readonly_connection()
        symbols = self._mt5.symbols_get()
        if symbols is None:
            raise RuntimeError(f"MT5 symbol discovery failed: {self._mt5.last_error()}")
        return [self.get_symbol_info(symbol.name) for symbol in symbols]

    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        self._require_readonly_connection()
        info = self._mt5.symbol_info(symbol)
        if info is None:
            raise KeyError(f"MT5 symbol not found: {symbol}")
        if not info.visible and not self._mt5.symbol_select(symbol, True):
            raise RuntimeError(f"MT5 could not select symbol {symbol}: {self._mt5.last_error()}")
        return SymbolInfo(
            symbol=info.name,
            description=info.description or info.name,
            contract_size=Decimal(str(info.trade_contract_size)),
            tick_size=Decimal(str(info.trade_tick_size)),
            tick_value=Decimal(str(info.trade_tick_value)),
            minimum_volume=Decimal(str(info.volume_min)),
            maximum_volume=Decimal(str(info.volume_max)),
            volume_step=Decimal(str(info.volume_step)),
            digits=int(info.digits),
            trade_allowed=bool(info.trade_mode),
        )

    def get_tick(self, symbol: str) -> Tick:
        self._require_readonly_connection()
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"MT5 tick unavailable for {symbol}: {self._mt5.last_error()}")
        return Tick(
            symbol=symbol,
            bid=Decimal(str(tick.bid)),
            ask=Decimal(str(tick.ask)),
            time=datetime.fromtimestamp(tick.time, tz=UTC),
        )

    def get_monitored_quotes(self, base_symbols: tuple[str, ...]) -> list[dict]:
        self._require_readonly_connection()
        available = self._mt5.symbols_get()
        if available is None:
            raise RuntimeError(f"MT5 symbol discovery failed: {self._mt5.last_error()}")
        quotes = []
        for base_symbol in base_symbols:
            normalized_base = "".join(character for character in base_symbol.upper() if character.isalnum())
            candidates = [
                symbol.name for symbol in available
                if normalized_base in "".join(character for character in symbol.name.upper() if character.isalnum())
            ]
            if not candidates:
                continue
            actual_symbol = min(
                candidates,
                key=lambda name: (
                    "".join(character for character in name.upper() if character.isalnum()) != normalized_base,
                    len(name),
                ),
            )
            info = self.get_symbol_info(actual_symbol)
            tick = self.get_tick(actual_symbol)
            quotes.append({
                "base_symbol": base_symbol,
                "symbol": actual_symbol,
                "bid": str(tick.bid),
                "ask": str(tick.ask),
                "time": tick.time.isoformat(),
                "digits": info.digits,
            })
        return quotes

    def get_historical_candles(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> list[Candle]:
        self._require_readonly_connection()
        if timeframe not in self.TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        mt5_timeframe = getattr(self._mt5, f"TIMEFRAME_{timeframe}")
        rates = self._mt5.copy_rates_range(symbol, mt5_timeframe, start, end)
        if rates is None:
            raise RuntimeError(f"MT5 history unavailable for {symbol}: {self._mt5.last_error()}")
        return [
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                time=datetime.fromtimestamp(int(rate["time"]), tz=UTC),
                open=Decimal(str(rate["open"])),
                high=Decimal(str(rate["high"])),
                low=Decimal(str(rate["low"])),
                close=Decimal(str(rate["close"])),
                volume=Decimal(str(rate["tick_volume"])),
            )
            for rate in rates
        ]

    def get_open_positions(self) -> list[dict]:
        self._require_readonly_connection()
        positions = self._mt5.positions_get()
        if positions is None:
            raise RuntimeError(f"MT5 positions unavailable: {self._mt5.last_error()}")
        return [
            {
                "ticket": str(position.ticket),
                "symbol": position.symbol,
                "direction": "BUY" if int(position.type) == int(self._mt5.POSITION_TYPE_BUY) else "SELL",
                "volume": str(position.volume),
                "price_open": str(position.price_open),
                "price_current": str(position.price_current),
                "profit": str(position.profit),
                "stop_loss": str(position.sl),
                "take_profit": str(position.tp),
                "simulated": False,
            }
            for position in positions
        ]

    def get_pending_orders(self) -> list[dict]:
        self._require_readonly_connection()
        orders = self._mt5.orders_get()
        if orders is None:
            raise RuntimeError(f"MT5 orders unavailable: {self._mt5.last_error()}")
        return [
            {"ticket": str(order.ticket), "symbol": order.symbol, "volume": str(order.volume_current)}
            for order in orders
        ]

    def get_order_history(self, start: datetime, end: datetime) -> list[dict]:
        self._require_readonly_connection()
        orders = self._mt5.history_orders_get(start, end)
        if orders is None:
            raise RuntimeError(f"MT5 order history unavailable: {self._mt5.last_error()}")
        return [{"ticket": str(order.ticket), "symbol": order.symbol, "state": int(order.state)} for order in orders]

    def get_deal_history(self, start: datetime, end: datetime) -> list[dict]:
        self._require_readonly_connection()
        deals = self._mt5.history_deals_get(start, end)
        if deals is None:
            raise RuntimeError(f"MT5 deal history unavailable: {self._mt5.last_error()}")
        return [
            {"ticket": str(deal.ticket), "order": str(deal.order), "symbol": deal.symbol, "profit": str(deal.profit)}
            for deal in deals
        ]

    def submit_order(self, symbol: str, direction: str, volume, stop_loss=None, take_profit=None, idempotency_key=None):
        raise PermissionError("Paper-trading mode is active; MT5 broker orders are disabled")

    def modify_position(self, *args, **kwargs):
        raise PermissionError("Paper-trading mode does not modify broker positions")

    def close_position(self, *args, **kwargs):
        raise PermissionError("Paper-trading mode does not close broker positions")

    def partial_close_position(self, *args, **kwargs):
        raise PermissionError("Paper-trading mode does not partially close broker positions")

    def _expected_trade_mode(self) -> int:
        constant = "ACCOUNT_TRADE_MODE_DEMO" if self._environment == "demo" else "ACCOUNT_TRADE_MODE_REAL"
        fallback = 0 if self._environment == "demo" else 2
        return int(getattr(self._mt5, constant, fallback))

    def _require_readonly_connection(self) -> None:
        state = self.connection_status()
        if not state["connected"]:
            raise ConnectionError(f"MT5 {self._environment} account is disconnected")
