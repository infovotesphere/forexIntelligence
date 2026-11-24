from pathlib import Path
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from shared.contracts.broker import Candle, Tick
from app.core.runtime import runtime_store

MODULE_PATH = Path(__file__).resolve()
ROOT = next(
    (
        ancestor
        for ancestor in MODULE_PATH.parents
        if (ancestor / "trading").exists() or (ancestor / "docker-compose.yml").exists()
    ),
    MODULE_PATH.parents[2] if len(MODULE_PATH.parents) > 2 else MODULE_PATH.parent,
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading.connectors.simulation import SimulationAdapter


simulation_adapter = SimulationAdapter()
simulation_adapter.connect()
_simulation_market_ticks: dict[str, Tick] = {}


def cache_simulation_market_candle(symbol: str, candle: Candle) -> None:
    if runtime_store.state.broker != "simulation":
        return
    normalized_symbol = symbol.upper()
    instrument = simulation_adapter.get_symbol_info(normalized_symbol)
    midpoint = candle.close.quantize(instrument.tick_size)
    half_spread = instrument.tick_size * 5
    bid = (midpoint - half_spread).quantize(instrument.tick_size)
    ask = (midpoint + half_spread).quantize(instrument.tick_size)
    if bid <= 0:
        raise ValueError(f"Real-market price for {normalized_symbol} is below its valid range")
    _simulation_market_ticks[normalized_symbol] = Tick(normalized_symbol, bid, ask, candle.time)


def get_live_mt5_tick(symbol: str) -> Tick | None:
    state = runtime_store.state
    normalized_symbol = symbol.upper()
    if state.broker == "simulation":
        return _simulation_market_ticks.get(normalized_symbol)
    if state.broker != "mt5":
        return None
    if not runtime_store.broker_connected():
        raise RuntimeError("The MT5 live price feed is disconnected")

    quote = next(
        (
            item for item in state.market_data
            if normalized_symbol in {
                str(item.get("base_symbol", "")).upper(),
                str(item.get("symbol", "")).upper(),
            }
        ),
        None,
    )
    if quote is None:
        raise RuntimeError(f"No MT5 live price is available for {normalized_symbol}")

    try:
        bid = Decimal(str(quote["bid"]))
        ask = Decimal(str(quote["ask"]))
        tick_time = datetime.fromisoformat(str(quote["time"]))
    except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
        raise RuntimeError(f"The MT5 live price for {normalized_symbol} is invalid") from exc
    if (
        tick_time.tzinfo is None
        or tick_time.utcoffset() is None
        or not bid.is_finite()
        or not ask.is_finite()
        or bid <= 0
        or ask < bid
    ):
        raise RuntimeError(f"The MT5 live price for {normalized_symbol} is invalid")
    tick_time = tick_time.astimezone(UTC)
    age = datetime.now(UTC) - tick_time
    if age > timedelta(seconds=30) or age < timedelta(seconds=-5):
        raise RuntimeError(f"The MT5 live price for {normalized_symbol} is stale")
    return Tick(normalized_symbol, bid, ask, tick_time)


simulation_adapter.set_tick_provider(get_live_mt5_tick)
