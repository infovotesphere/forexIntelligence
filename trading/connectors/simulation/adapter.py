from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import math
import uuid

from shared.contracts.broker import AccountInfo, BrokerResponse, Candle, SymbolInfo, Tick
from trading.connectors.base import BrokerConnector


class SimulationAdapter(BrokerConnector):
    """Deterministic, clearly simulated broker for Linux development and tests."""

    REFERENCE_PRICES = {
        "EURUSD": Decimal("1.08500"),
        "GBPUSD": Decimal("1.27000"),
        "USDJPY": Decimal("150.000"),
        "USDCHF": Decimal("0.88000"),
        "USDCAD": Decimal("1.37000"),
        "AUDUSD": Decimal("0.66000"),
        "NZDUSD": Decimal("0.61000"),
        "EURGBP": Decimal("0.85500"),
        "EURJPY": Decimal("163.500"),
        "EURAUD": Decimal("1.65000"),
        "EURCAD": Decimal("1.48000"),
        "EURCHF": Decimal("0.96000"),
        "EURNZD": Decimal("1.78000"),
        "GBPJPY": Decimal("190.500"),
        "GBPAUD": Decimal("1.92000"),
        "GBPCAD": Decimal("1.72000"),
        "GBPCHF": Decimal("1.12000"),
        "GBPNZD": Decimal("2.08000"),
        "AUDJPY": Decimal("99.000"),
        "AUDCAD": Decimal("0.90500"),
        "AUDNZD": Decimal("1.09000"),
        "AUDCHF": Decimal("0.56500"),
        "CADJPY": Decimal("109.500"),
        "CADCHF": Decimal("0.64000"),
        "CHFJPY": Decimal("170.500"),
        "NZDJPY": Decimal("91.500"),
        "NZDCAD": Decimal("0.83500"),
        "NZDCHF": Decimal("0.53500"),
        "XAUUSD": Decimal("2300.00"),
        "BTCUSD": Decimal("95000.00"),
        "ETHUSD": Decimal("3500.00"),
        "BNBUSD": Decimal("600.00"),
        "SOLUSD": Decimal("180.00"),
        "XRPUSD": Decimal("2.4000"),
        "ADAUSD": Decimal("0.7200"),
        "DOGEUSD": Decimal("0.2000"),
        "LTCUSD": Decimal("100.00"),
        "BCHUSD": Decimal("400.00"),
        "AVAXUSD": Decimal("35.00"),
    }
    SYMBOLS = tuple(REFERENCE_PRICES)
    CRYPTO_SYMBOLS = frozenset({
        "BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD",
        "ADAUSD", "DOGEUSD", "LTCUSD", "BCHUSD", "AVAXUSD",
    })
    CRYPTO_4_DIGIT_SYMBOLS = frozenset({"XRPUSD", "ADAUSD", "DOGEUSD"})

    def __init__(self) -> None:
        self._connected = False
        self._tick_provider: Callable[[str], Tick | None] | None = None
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
        self._balance = Decimal("10000")
        self._submitted: dict[str, BrokerResponse] = {}
        self._positions: dict[str, dict] = {}
        self._pending_orders: dict[str, dict] = {}
        self._deals: list[dict] = []

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def set_tick_provider(self, provider: Callable[[str], Tick | None] | None) -> None:
        self._tick_provider = provider

    def connection_status(self) -> dict:
        return {"connected": self._connected, "environment": "simulation", "simulated": True}

    def get_account_info(self) -> AccountInfo:
        self._require_connection()
        positions = self.get_open_positions()
        floating_profit = sum((Decimal(position["profit"]) for position in positions), Decimal("0"))
        equity = self._balance + floating_profit
        return replace(
            self._account,
            balance=self._balance,
            equity=equity,
            free_margin=equity,
        )

    def get_instruments(self) -> list[SymbolInfo]:
        self._require_connection()
        return [self.get_symbol_info(symbol) for symbol in self.SYMBOLS]

    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        self._require_connection()
        if symbol not in self.SYMBOLS:
            raise KeyError(f"Unknown simulated symbol: {symbol}")
        if symbol == "XAUUSD" or symbol in self.CRYPTO_SYMBOLS - self.CRYPTO_4_DIGIT_SYMBOLS:
            digits = 2
        elif symbol in self.CRYPTO_4_DIGIT_SYMBOLS:
            digits = 4
        else:
            digits = 3 if symbol.endswith("JPY") else 5
        tick_size = Decimal("0.01") if digits == 2 else Decimal(1).scaleb(-digits)
        is_crypto = symbol in self.CRYPTO_SYMBOLS
        return SymbolInfo(
            symbol=symbol,
            description=(
                f"{symbol[:-3]}/USD cryptocurrency"
                if is_crypto
                else "Gold / US Dollar" if symbol == "XAUUSD"
                else f"{symbol[:3]}/{symbol[3:]} forex pair"
            ),
            contract_size=Decimal("1") if is_crypto else Decimal("100000"),
            tick_size=tick_size,
            tick_value=tick_size if is_crypto else Decimal("1"),
            minimum_volume=Decimal("0.001") if is_crypto else Decimal("0.01"),
            maximum_volume=Decimal("100"),
            volume_step=Decimal("0.001") if is_crypto else Decimal("0.01"),
            digits=digits,
            trade_allowed=True,
        )

    def get_tick(self, symbol: str) -> Tick:
        self._require_connection()
        if self._tick_provider is not None:
            tick = self._tick_provider(symbol)
            if tick is not None:
                return tick
        info = self.get_symbol_info(symbol)
        seed = int(hashlib.sha256(f"{symbol}:{datetime.now(UTC).replace(microsecond=0)}".encode()).hexdigest()[:8], 16)
        base = self.REFERENCE_PRICES[symbol]
        offset = Decimal(seed % 50).scaleb(-info.digits)
        bid = (base + offset).quantize(tick_size := info.tick_size)
        ask = (bid + tick_size * 10).quantize(tick_size)
        return Tick(symbol=symbol, bid=bid, ask=ask, time=datetime.now(UTC))

    def get_historical_candles(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> list[Candle]:
        self._require_connection()
        info = self.get_symbol_info(symbol)
        minutes = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}.get(timeframe)
        if minutes is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        candles: list[Candle] = []
        interval = minutes * 60
        current = datetime.fromtimestamp(int(start.timestamp() // interval) * interval, UTC)
        index = int(current.timestamp() // interval)
        base = self.REFERENCE_PRICES[symbol]
        phase = int(hashlib.sha256(f"{symbol}:{timeframe}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF * math.tau
        scale = base * Decimal("0.0008") * Decimal(str(math.sqrt(max(minutes / 60, 0.1))))

        def noise(bar_index: int, salt: str) -> float:
            digest = hashlib.sha256(f"{symbol}:{timeframe}:{bar_index}:{salt}".encode()).hexdigest()[:8]
            return int(digest, 16) / 0xFFFFFFFF

        def price_at(bar_index: int) -> Decimal:
            wave = (
                0.75 * math.sin(bar_index / 67 + phase)
                + 0.35 * math.sin(bar_index / 19 + phase * 1.7)
                + 0.15 * math.sin(bar_index / 4.7 + phase * 2.3)
                + (noise(bar_index, "price") - 0.5) * 0.44
            )
            return (base + scale * Decimal(str(wave))).quantize(info.tick_size)

        while current <= end:
            open_price = price_at(index)
            close = price_at(index + 1)
            high_wick = scale * Decimal(str(0.08 + noise(index, "high") * 0.42))
            low_wick = scale * Decimal(str(0.08 + noise(index, "low") * 0.42))
            high = (max(open_price, close) + high_wick).quantize(info.tick_size)
            low = (min(open_price, close) - low_wick).quantize(info.tick_size)
            volume = Decimal(str(round(70 + noise(index, "volume") * 230)))
            candles.append(Candle(symbol, timeframe, current, open_price, high, low, close, volume))
            current += timedelta(minutes=minutes)
            index += 1
        return candles

    def get_open_positions(self) -> list[dict]:
        self._require_connection()
        positions = []
        for ticket, position in list(self._positions.items()):
            self._record_entry_deal(position)
            tick = self.get_tick(position["symbol"])
            close_price = tick.bid if position["direction"] == "BUY" else tick.ask
            stop_loss = Decimal(position["stop_loss"])
            take_profit_price = Decimal(position["take_profit"])
            take_profit = take_profit_price if take_profit_price > 0 else None
            stopped = stop_loss > 0 and (
                close_price <= stop_loss if position["direction"] == "BUY" else close_price >= stop_loss
            )
            targeted = (
                take_profit is not None
                and (close_price >= take_profit if position["direction"] == "BUY" else close_price <= take_profit)
            )
            if stopped or targeted:
                self._close_position(ticket, close_price, "STOP_LOSS" if stopped else "TAKE_PROFIT")
                continue
            current = dict(position)
            current["price_current"] = str(close_price)
            current["profit"] = str(self._calculate_profit(
                position["symbol"],
                position["direction"],
                Decimal(position["volume"]),
                Decimal(position["price_open"]),
                close_price,
            ))
            positions.append(current)
        return positions

    def get_pending_orders(self) -> list[dict]:
        self._require_connection()
        pending_orders = []
        for ticket, pending in list(self._pending_orders.items()):
            tick = self.get_tick(pending["symbol"])
            triggered = (
                tick.ask >= Decimal(pending["stop_price"])
                if pending["order_type"] == "BUY_STOP"
                else tick.bid <= Decimal(pending["stop_price"])
            )
            if not triggered:
                pending_orders.append({key: value for key, value in pending.items() if key != "idempotency_key"})
                continue

            self._pending_orders.pop(ticket)
            position = self._create_position(
                pending["symbol"],
                pending["direction"],
                Decimal(pending["volume"]),
                Decimal(pending["stop_price"]),
                Decimal(pending["stop_loss"]),
                Decimal(pending["take_profit"]),
                Decimal(pending["initial_risk"]),
            )
            self._submitted[pending["idempotency_key"]] = BrokerResponse(
                True,
                ticket,
                position["ticket"],
                "filled",
                "Pending stop order triggered",
                True,
            )
        return pending_orders

    def cancel_pending_order(self, ticket: str) -> dict:
        self._require_connection()
        pending = self._pending_orders.pop(ticket, None)
        if pending is None:
            raise KeyError(f"Unknown simulated pending order: {ticket}")
        return {
            **{key: value for key, value in pending.items() if key != "idempotency_key"},
            "status": "cancelled",
        }

    def submit_order(
        self,
        symbol: str,
        direction: str,
        volume,
        stop_loss=None,
        take_profit=None,
        idempotency_key: str | None = None,
        max_risk_amount: Decimal | None = None,
        max_aggregate_risk_amount: Decimal | None = None,
        max_open_positions: int | None = None,
        order_type: str = "MARKET",
        stop_price=None,
    ) -> BrokerResponse:
        self._require_connection()
        symbol = symbol.upper()
        direction = direction.upper()
        order_type = order_type.upper()
        if direction not in {"BUY", "SELL"}:
            raise ValueError("Direction must be BUY or SELL")
        if order_type not in {"MARKET", "BUY_STOP", "SELL_STOP"}:
            raise ValueError("Order type must be MARKET, BUY_STOP or SELL_STOP")
        if (order_type == "BUY_STOP" and direction != "BUY") or (order_type == "SELL_STOP" and direction != "SELL"):
            raise ValueError("Stop order direction does not match its order type")
        if order_type == "MARKET" and stop_price is not None:
            raise ValueError("Market orders cannot specify a stop entry price")
        if order_type != "MARKET" and stop_price is None:
            raise ValueError("Buy stop and sell stop orders require an entry price")

        instrument = self.get_symbol_info(symbol)
        volume = Decimal(str(volume))
        stop_loss = Decimal(str(stop_loss)) if stop_loss is not None else None
        take_profit = Decimal(str(take_profit)) if take_profit is not None else None
        stop_price = Decimal(str(stop_price)) if stop_price is not None else None
        if volume < instrument.minimum_volume or volume > instrument.maximum_volume:
            raise ValueError("Volume is outside the simulated instrument limits")
        if volume % instrument.volume_step != 0:
            raise ValueError("Volume must match the simulated instrument volume step")
        if (
            (stop_loss is not None and stop_loss % instrument.tick_size != 0)
            or (take_profit is not None and take_profit % instrument.tick_size != 0)
            or (stop_price is not None and stop_price % instrument.tick_size != 0)
        ):
            raise ValueError("Stop loss and take profit must match the instrument tick size")
        key = idempotency_key or str(uuid.uuid4())
        if key in self._submitted:
            previous = self._submitted[key]
            return BrokerResponse(True, previous.broker_order_id, previous.broker_position_id, "IDEMPOTENT_RETURN", "Existing simulated order returned", True)

        tick = self.get_tick(symbol)
        if order_type == "MARKET":
            entry = tick.ask if direction == "BUY" else tick.bid
            exit_quote = tick.bid if direction == "BUY" else tick.ask
        else:
            entry = stop_price
            exit_quote = stop_price
            if order_type == "BUY_STOP" and stop_price <= tick.ask:
                raise ValueError("A buy stop entry must be above the current ask")
            if order_type == "SELL_STOP" and stop_price >= tick.bid:
                raise ValueError("A sell stop entry must be below the current bid")

        if stop_loss is not None and (
            (direction == "BUY" and stop_loss >= exit_quote)
            or (direction == "SELL" and stop_loss <= exit_quote)
        ):
            raise ValueError("Stop loss must be beyond the entry price in the loss direction")
        if take_profit is not None and (
            (direction == "BUY" and take_profit <= exit_quote)
            or (direction == "SELL" and take_profit >= exit_quote)
        ):
            raise ValueError("Take profit must be beyond the entry price in the profit direction")

        pending_orders = self.get_pending_orders()
        open_positions = self.get_open_positions()
        if max_open_positions is not None and len(open_positions) + len(pending_orders) >= max_open_positions:
            raise ValueError("The configured maximum number of open positions has been reached")
        trade_risk = (
            self._calculate_profit(symbol, direction, volume, entry, stop_loss).copy_abs()
            if stop_loss is not None
            else Decimal("0")
        )
        if stop_loss is not None and max_risk_amount is not None and trade_risk > max_risk_amount:
            raise ValueError("Trade risk exceeds the configured per-trade risk limit")
        open_risk = sum(
            (Decimal(item["initial_risk"]) for item in [*self._positions.values(), *self._pending_orders.values()]),
            Decimal("0"),
        )
        if (
            stop_loss is not None
            and max_aggregate_risk_amount is not None
            and open_risk + trade_risk > max_aggregate_risk_amount
        ):
            raise ValueError("Trade would exceed the configured aggregate open-risk limit")

        if order_type != "MARKET":
            pending_id = f"SIM-PENDING-{uuid.uuid4()}"
            pending = {
                "ticket": pending_id,
                "symbol": symbol,
                "order_type": order_type,
                "direction": direction,
                "volume": str(volume),
                "stop_price": str(stop_price),
                "stop_loss": str(stop_loss) if stop_loss is not None else "0",
                "take_profit": str(take_profit) if take_profit is not None else "0",
                "initial_risk": str(trade_risk),
                "idempotency_key": key,
                "created_at": datetime.now(UTC).isoformat(),
                "simulated": True,
            }
            self._pending_orders[pending_id] = pending
            response = BrokerResponse(True, pending_id, None, "placed", "Pending stop order accepted", True)
            self._submitted[key] = response
            return response

        position = self._create_position(symbol, direction, volume, entry, stop_loss, take_profit, trade_risk)
        response = BrokerResponse(True, position["ticket"], position["ticket"], "filled", "Simulated execution accepted", True)
        self._submitted[key] = response
        return response

    def _create_position(
        self,
        symbol: str,
        direction: str,
        volume: Decimal,
        entry: Decimal,
        stop_loss: Decimal | None,
        take_profit: Decimal | None,
        trade_risk: Decimal,
    ) -> dict:
        broker_id = f"SIM-{uuid.uuid4()}"
        position = {
            "ticket": broker_id,
            "symbol": symbol,
            "direction": direction,
            "volume": str(volume),
            "price_open": str(entry),
            "price_current": str(entry),
            "profit": "0",
            "stop_loss": str(stop_loss) if stop_loss is not None else "0",
            "take_profit": str(take_profit) if take_profit is not None else "0",
            "initial_risk": str(trade_risk),
            "open_time": datetime.now(UTC).isoformat(),
            "simulated": True,
        }
        self._positions[broker_id] = position
        self._record_entry_deal(position)
        return dict(position)

    def _record_entry_deal(self, position: dict) -> None:
        order = str(position["ticket"])
        if any(deal.get("order") == order and deal.get("deal_type") == "ENTRY" for deal in self._deals):
            return
        self._deals.append({
            "ticket": f"{order}-OPEN",
            "order": order,
            "symbol": position["symbol"],
            "direction": position["direction"],
            "volume": str(position["volume"]),
            "price": str(position["price_open"]),
            "profit": "0",
            "commission": "0",
            "swap": "0",
            "net_profit": "0",
            "time": str(position.get("open_time") or datetime.now(UTC).isoformat()),
            "simulated": True,
            "deal_type": "ENTRY",
        })

    def close_position(self, ticket: str) -> dict:
        self._require_connection()
        position = self._positions.get(ticket)
        if position is None:
            raise KeyError(f"Unknown simulated position: {ticket}")
        tick = self.get_tick(position["symbol"])
        close_price = tick.bid if position["direction"] == "BUY" else tick.ask
        return self._close_position(ticket, close_price, "MANUAL")

    def close_positions(self, tickets: list[str]) -> list[dict]:
        self._require_connection()
        if not tickets:
            raise ValueError("Select at least one open position")
        if len(set(tickets)) != len(tickets):
            raise ValueError("A position can only be selected once")
        missing = [ticket for ticket in tickets if ticket not in self._positions]
        if missing:
            raise KeyError(f"Unknown simulated position: {missing[0]}")

        deals = []
        for ticket in tickets:
            position = self._positions[ticket]
            tick = self.get_tick(position["symbol"])
            close_price = tick.bid if position["direction"] == "BUY" else tick.ask
            deals.append(self._close_position(ticket, close_price, "MANUAL"))
        return deals

    def modify_position(
        self,
        ticket: str,
        stop_loss,
        take_profit,
        max_risk_amount: Decimal | None = None,
        max_aggregate_risk_amount: Decimal | None = None,
    ) -> dict:
        self._require_connection()
        position = self._positions.get(ticket)
        if position is None:
            raise KeyError(f"Unknown simulated position: {ticket}")

        instrument = self.get_symbol_info(position["symbol"])
        stop_loss = Decimal(str(stop_loss))
        take_profit = Decimal(str(take_profit))
        if stop_loss < 0 or take_profit < 0:
            raise ValueError("Stop loss and take profit cannot be negative")
        if (
            (stop_loss > 0 and stop_loss % instrument.tick_size != 0)
            or (take_profit > 0 and take_profit % instrument.tick_size != 0)
        ):
            raise ValueError("Stop loss and take profit must match the instrument tick size")

        tick = self.get_tick(position["symbol"])
        exit_quote = tick.bid if position["direction"] == "BUY" else tick.ask
        if stop_loss > 0 and (
            (position["direction"] == "BUY" and stop_loss >= exit_quote)
            or (position["direction"] == "SELL" and stop_loss <= exit_quote)
        ):
            comparison = "below current bid" if position["direction"] == "BUY" else "above current ask"
            raise ValueError(f"Stop loss for {position['direction']} must be {comparison} ({exit_quote})")
        if take_profit > 0 and (
            (position["direction"] == "BUY" and take_profit <= exit_quote)
            or (position["direction"] == "SELL" and take_profit >= exit_quote)
        ):
            comparison = "above current bid" if position["direction"] == "BUY" else "below current ask"
            raise ValueError(f"Take profit for {position['direction']} must be {comparison} ({exit_quote})")

        parsed_stop_loss = stop_loss if stop_loss > 0 else None
        trade_risk = (
            self._calculate_profit(
                position["symbol"],
                position["direction"],
                Decimal(position["volume"]),
                Decimal(position["price_open"]),
                parsed_stop_loss,
            ).copy_abs()
            if parsed_stop_loss is not None
            else Decimal("0")
        )
        if max_risk_amount is not None and trade_risk > max_risk_amount:
            raise ValueError("Trade risk exceeds the configured per-trade risk limit")
        open_risk = sum(
            (
                Decimal(item["initial_risk"])
                for other_ticket, item in self._positions.items()
                if other_ticket != ticket
            ),
            Decimal("0"),
        ) + sum(
            (Decimal(item["initial_risk"]) for item in self._pending_orders.values()),
            Decimal("0"),
        )
        if max_aggregate_risk_amount is not None and open_risk + trade_risk > max_aggregate_risk_amount:
            raise ValueError("Trade would exceed the configured aggregate open-risk limit")

        position["stop_loss"] = str(parsed_stop_loss) if parsed_stop_loss is not None else "0"
        position["take_profit"] = str(take_profit) if take_profit > 0 else "0"
        position["initial_risk"] = str(trade_risk)
        return dict(position)

    def get_deal_history(self) -> list[dict]:
        self._require_connection()
        for position in self._positions.values():
            self._record_entry_deal(position)
        return [dict(deal) for deal in reversed(self._deals)]

    def export_state(self) -> dict:
        return {
            "balance": str(self._balance),
            "positions": [dict(position) for position in self._positions.values()],
            "pending_orders": [dict(order) for order in self._pending_orders.values()],
            "deals": [dict(deal) for deal in self._deals],
        }

    def restore_state(self, state: dict) -> None:
        if not isinstance(state, dict):
            return
        try:
            balance = Decimal(str(state.get("balance", "10000")))
            positions = state.get("positions", [])
            pending_orders = state.get("pending_orders", [])
            deals = state.get("deals", state.get("closed_deals", []))
            if (
                balance <= 0
                or not isinstance(positions, list)
                or not isinstance(pending_orders, list)
                or not isinstance(deals, list)
            ):
                return
            self._balance = balance
            self._positions = {
                str(position["ticket"]): dict(position)
                for position in positions
                if isinstance(position, dict) and position.get("ticket") and position.get("symbol") in self.SYMBOLS
            }
            self._pending_orders = {
                str(order["ticket"]): dict(order)
                for order in pending_orders
                if isinstance(order, dict)
                and order.get("ticket")
                and order.get("symbol") in self.SYMBOLS
                and order.get("order_type") in {"BUY_STOP", "SELL_STOP"}
                and order.get("idempotency_key")
            }
            self._deals = [dict(deal) for deal in deals if isinstance(deal, dict)]
        except (ArithmeticError, KeyError, TypeError, ValueError):
            return

    def _calculate_profit(
        self,
        symbol: str,
        direction: str,
        volume: Decimal,
        entry: Decimal,
        exit_price: Decimal,
    ) -> Decimal:
        instrument = self.get_symbol_info(symbol)
        price_change = exit_price - entry if direction == "BUY" else entry - exit_price
        return (price_change / instrument.tick_size * instrument.tick_value * volume).quantize(Decimal("0.01"))

    def _close_position(self, ticket: str, close_price: Decimal, reason: str) -> dict:
        position = self._positions.pop(ticket)
        profit = self._calculate_profit(
            position["symbol"],
            position["direction"],
            Decimal(position["volume"]),
            Decimal(position["price_open"]),
            close_price,
        )
        self._balance += profit
        deal = {
            "ticket": f"{ticket}-CLOSE",
            "order": ticket,
            "symbol": position["symbol"],
            "direction": position["direction"],
            "volume": position["volume"],
            "price": str(close_price),
            "profit": str(profit),
            "commission": "0",
            "swap": "0",
            "net_profit": str(profit),
            "time": datetime.now(UTC).isoformat(),
            "simulated": True,
            "deal_type": "EXIT",
            "close_reason": reason,
        }
        self._deals.append(deal)
        return dict(deal)

    def _require_connection(self) -> None:
        if not self._connected:
            raise ConnectionError("Simulation broker is disconnected")
