from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from trading.strategies.base import StrategySignal
from trading.signals.validator import validate_signal


def generate_validated_signals(symbol: str, timeframe: str, candles, strategies, now: datetime | None = None) -> list[dict]:
    if len(candles) < 2:
        return []
    now = now or datetime.now(UTC)
    completed = candles[:-1]
    if (now - completed[-1].time).total_seconds() > 24 * 60 * 60:
        return []

    results: list[dict] = []
    for strategy in strategies:
        candidate: StrategySignal | None = strategy.evaluate(symbol, timeframe, completed)
        if candidate is None:
            continue
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
        entry = Decimal(str(candidate.entry))
        stop = Decimal(str(candidate.stop_loss))
        risk = entry - stop if candidate.direction == "BUY" else stop - entry
        reward = Decimal(str(candidate.take_profit_1)) - entry if candidate.direction == "BUY" else entry - Decimal(str(candidate.take_profit_1))
        results.append({
            "signal_id": str(uuid4()),
            "symbol": symbol,
            "direction": candidate.direction,
            "strategy": candidate.strategy,
            "timeframe": timeframe,
            "entry": str(entry),
            "stop_loss": str(stop),
            "tp1": str(candidate.take_profit_1),
            "tp2": str(candidate.take_profit_2),
            "tp3": str(candidate.take_profit_3),
            "risk_reward_ratio": str(reward / risk),
            "quality_score": candidate.quality_score,
            "explanation": candidate.explanation,
            "status": "VALIDATED",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=4)).isoformat(),
        })
    return results
