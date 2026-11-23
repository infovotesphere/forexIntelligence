from datetime import datetime
from decimal import Decimal

from shared.contracts.broker import Candle

from app.core.runtime import runtime_store


def get_mt5_candles(symbol: str, timeframe: str) -> tuple[str, list[Candle]] | None:
    snapshot = runtime_store.get_market_candle_snapshot(symbol, timeframe)
    if snapshot is None:
        return None
    actual_symbol = snapshot["symbol"]
    candles = [
        Candle(
            symbol=actual_symbol,
            timeframe=timeframe,
            time=datetime.fromisoformat(candle["time"]),
            open=Decimal(candle["open"]),
            high=Decimal(candle["high"]),
            low=Decimal(candle["low"]),
            close=Decimal(candle["close"]),
            volume=Decimal(candle["volume"]),
        )
        for candle in snapshot["candles"]
    ]
    return actual_symbol, candles
