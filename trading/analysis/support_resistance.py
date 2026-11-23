from collections.abc import Sequence


def support_resistance(candles: Sequence, tolerance: float = 0.001) -> tuple[list[float], list[float]]:
    if not candles:
        return [], []
    lows = sorted(set(round(float(candle.low), 5) for candle in candles))
    highs = sorted(set(round(float(candle.high), 5) for candle in candles), reverse=True)
    current = float(candles[-1].close)
    supports = [level for level in lows if level <= current]
    resistances = [level for level in highs if level >= current]
    return supports[-3:], resistances[:3]
