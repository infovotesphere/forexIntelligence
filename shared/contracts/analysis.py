from dataclasses import dataclass


@dataclass(frozen=True)
class IndicatorSet:
    ema20: float
    ema50: float
    ema200: float
    rsi14: float
    macd: float
    macd_signal: float
    atr14: float
    bollinger_upper: float
    bollinger_lower: float
    adx: float
    stochastic_k: float
