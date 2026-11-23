from datetime import UTC, datetime, timedelta
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

from trading.strategies.base import StrategySignal
from trading.signals.validator import round_to_tick, validate_signal


def generate_validated_signals(
    symbol: str,
    timeframe: str,
    candles,
    strategies,
    now: datetime | None = None,
    tick_size: Decimal | None = None,
) -> list[dict]:
    if len(candles) < 2:
        return []
    now = now or datetime.now(UTC)
    completed = candles[:-1]
    if (now - completed[-1].time).total_seconds() > 24 * 60 * 60:
        return []
    price_step = tick_size or Decimal(1).scaleb(Decimal(str(completed[-1].close)).as_tuple().exponent)
    results: list[dict] = []
    for strategy in strategies:
        candidate: StrategySignal | None = strategy.evaluate(symbol, timeframe, completed)
        if candidate is None:
            continue
        prices = {
            field: round_to_tick(getattr(candidate, field), price_step)
            for field in ("entry", "stop_loss", "take_profit_1", "take_profit_2", "take_profit_3")
        }
        candidate = replace(candidate, **{field: float(price) for field, price in prices.items()})
        try:
            validate_signal(candidate)
        except ValueError as exc:
            results.append({
                "status": "REJECTED",
                "symbol": symbol,
                "strategy": candidate.strategy,
                "timeframe": timeframe,
                "rejection_reason": str(exc),
                "created_at": now.isoformat(),
            })
            continue
        entry = prices["entry"]
        stop = prices["stop_loss"]
        risk = entry - stop if candidate.direction == "BUY" else stop - entry
        reward = prices["take_profit_3"] - entry if candidate.direction == "BUY" else entry - prices["take_profit_3"]
        results.append({
            "signal_id": str(uuid4()),
            "symbol": symbol,
            "direction": candidate.direction,
            "strategy": candidate.strategy,
            "timeframe": timeframe,
            "entry": str(entry),
            "stop_loss": str(stop),
            "tp1": str(prices["take_profit_1"]),
            "tp2": str(prices["take_profit_2"]),
            "tp3": str(prices["take_profit_3"]),
            "risk_reward_ratio": str(reward / risk),
            "quality_score": candidate.quality_score,
            "explanation": candidate.explanation,
            "status": "VALIDATED",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=4)).isoformat(),
        })
    return results
