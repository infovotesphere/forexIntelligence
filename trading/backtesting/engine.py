from dataclasses import replace
from decimal import Decimal

from shared.contracts.analysis import IndicatorSet
from trading.analysis.indicators import calculate_indicator_history
from trading.signals.validator import SignalValidationError, round_to_tick, validate_signal
from trading.strategies.base import Strategy


def backtest_strategy(
    symbol: str,
    timeframe: str,
    candles: list,
    strategy: Strategy,
    tick_size: Decimal | None = None,
) -> dict:
    trades: list[dict] = []
    rejected = 0
    index = 1
    price_step = tick_size or Decimal(1).scaleb(Decimal(str(candles[-1].close)).as_tuple().exponent)
    indicators = calculate_indicator_history(candles)

    while index < len(candles) - 1:
        candidate = strategy.evaluate(
            symbol,
            timeframe,
            candles[:index + 1],
            context={"indicators": indicators[index]},
        )
        if candidate is None:
            index += 1
            continue
        prices = {
            field: round_to_tick(getattr(candidate, field), price_step)
            for field in ("entry", "stop_loss", "take_profit_1", "take_profit_2", "take_profit_3")
        }
        candidate = replace(candidate, **{field: float(price) for field, price in prices.items()})
        try:
            validate_signal(candidate)
        except SignalValidationError:
            rejected += 1
            index += 1
            continue

        entry = prices["entry"]
        stop = prices["stop_loss"]
        target = prices["take_profit_3"]
        risk = entry - stop if candidate.direction == "BUY" else stop - entry
        outcome = "OPEN"
        exit_price: Decimal | None = None
        exit_index: int | None = None
        ambiguous_exit = False

        for future_index in range(index + 1, len(candles)):
            candle = candles[future_index]
            if candidate.direction == "BUY":
                stop_hit = candle.low <= stop
                target_hit = candle.high >= target
            else:
                stop_hit = candle.high >= stop
                target_hit = candle.low <= target

            if stop_hit:
                outcome = "STOP_LOSS"
                exit_price = stop
                exit_index = future_index
                ambiguous_exit = target_hit
                break
            if target_hit:
                outcome = "TAKE_PROFIT"
                exit_price = target
                exit_index = future_index
                break

        r_multiple = None
        if outcome == "STOP_LOSS":
            r_multiple = Decimal("-1")
        elif outcome == "TAKE_PROFIT":
            reward = target - entry if candidate.direction == "BUY" else entry - target
            r_multiple = reward / risk

        trades.append({
            "signal_time": candles[index].time.isoformat(),
            "exit_time": candles[exit_index].time.isoformat() if exit_index is not None else None,
            "direction": candidate.direction,
            "entry": str(entry),
            "stop_loss": str(stop),
            "take_profit": str(target),
            "exit_price": str(exit_price) if exit_price is not None else None,
            "outcome": outcome,
            "r_multiple": str(r_multiple) if r_multiple is not None else None,
            "candles_held": exit_index - index if exit_index is not None else len(candles) - index - 1,
            "ambiguous_exit": ambiguous_exit,
        })

        if exit_index is None:
            break
        index = exit_index + 1

    resolved = [trade for trade in trades if trade["r_multiple"] is not None]
    wins = [Decimal(trade["r_multiple"]) for trade in resolved if Decimal(trade["r_multiple"]) > 0]
    losses = [Decimal(trade["r_multiple"]) for trade in resolved if Decimal(trade["r_multiple"]) < 0]
    net_r = sum((Decimal(trade["r_multiple"]) for trade in resolved), Decimal("0"))
    peak = Decimal("0")
    equity = Decimal("0")
    max_drawdown = Decimal("0")
    equity_curve: list[dict] = []
    for trade in resolved:
        equity += Decimal(trade["r_multiple"])
        peak = max(peak, equity)
        drawdown = peak - equity
        max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append({
            "trade_number": len(equity_curve) + 1,
            "time": trade["exit_time"],
            "cumulative_r": str(equity),
            "drawdown_r": str(drawdown),
        })

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "summary": {
            "total_trades": len(trades),
            "resolved_trades": len(resolved),
            "wins": len(wins),
            "losses": len(losses),
            "open_trades": len(trades) - len(resolved),
            "rejected_candidates": rejected,
            "win_rate_percent": str(Decimal(len(wins)) * 100 / len(resolved)) if resolved else None,
            "net_r": str(net_r),
            "average_r": str(net_r / len(resolved)) if resolved else None,
            "profit_factor": str(sum(wins, Decimal("0")) / abs(sum(losses, Decimal("0")))) if losses else None,
            "max_drawdown_r": str(max_drawdown),
        },
    }
