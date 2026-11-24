from collections.abc import Sequence

from shared.contracts.analysis import IndicatorSet


def ema(values: Sequence[float], period: int) -> list[float]:
    if period < 1:
        raise ValueError("EMA period must be positive")
    if not values:
        return []
    multiplier = 2.0 / (period + 1.0)
    result = [float(values[0])]
    for value in values[1:]:
        result.append((float(value) - result[-1]) * multiplier + result[-1])
    return result


def rsi(values: Sequence[float], period: int = 14) -> list[float]:
    if period < 1:
        raise ValueError("RSI period must be positive")
    if len(values) < 2:
        return [50.0] * len(values)
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(values, values[1:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    result = [50.0]
    average_gain = sum(gains[:period]) / period if len(gains) >= period else sum(gains) / len(gains)
    average_loss = sum(losses[:period]) / period if len(losses) >= period else sum(losses) / len(losses)
    for index in range(len(gains)):
        if index >= period:
            average_gain = (average_gain * (period - 1) + gains[index]) / period
            average_loss = (average_loss * (period - 1) + losses[index]) / period
        if average_loss == 0:
            result.append(100.0)
        else:
            result.append(100.0 - (100.0 / (1.0 + average_gain / average_loss)))
    return result


def _rsi_prefix_values(values: Sequence[float], period: int = 14) -> list[float]:
    if not values:
        return []
    if len(values) < 2:
        return [50.0]

    result = [50.0]
    gain_sum = 0.0
    loss_sum = 0.0
    average_gain = 0.0
    average_loss = 0.0
    for index, (previous, current) in enumerate(zip(values, values[1:]), start=1):
        change = current - previous
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        if index <= period:
            gain_sum += gain
            loss_sum += loss
            average_gain = gain_sum / index if index < period else gain_sum / period
            average_loss = loss_sum / index if index < period else loss_sum / period
        else:
            average_gain = (average_gain * (period - 1) + gain) / period
            average_loss = (average_loss * (period - 1) + loss) / period
        result.append(100.0 if average_loss == 0 else 100.0 - (100.0 / (1.0 + average_gain / average_loss)))
    return result


def macd(values: Sequence[float]) -> tuple[list[float], list[float]]:
    ema12 = ema(values, 12)
    ema26 = ema(values, 26)
    line = [fast - slow for fast, slow in zip(ema12, ema26)]
    signal = ema(line, 9)
    return line, signal


def atr(candles: Sequence, period: int = 14) -> list[float]:
    if period < 1:
        raise ValueError("ATR period must be positive")
    if not candles:
        return []
    true_ranges = [float(candles[0].high - candles[0].low)]
    for previous, current in zip(candles, candles[1:]):
        true_ranges.append(max(
            float(current.high - current.low),
            abs(float(current.high - previous.close)),
            abs(float(current.low - previous.close)),
        ))
    result: list[float] = []
    for index in range(len(true_ranges)):
        window = true_ranges[max(0, index - period + 1):index + 1]
        result.append(sum(window) / len(window))
    return result


def bollinger_bands(values: Sequence[float], period: int = 20, deviations: float = 2.0) -> tuple[list[float], list[float]]:
    middle = ema(values, period)
    upper: list[float] = []
    lower: list[float] = []
    for index, center in enumerate(middle):
        window = values[max(0, index - period + 1):index + 1]
        mean = sum(window) / len(window)
        variance = sum((value - mean) ** 2 for value in window) / len(window)
        width = deviations * variance ** 0.5
        upper.append(center + width)
        lower.append(center - width)
    return upper, lower


def stochastic(candles: Sequence, period: int = 14) -> list[float]:
    if period < 1:
        raise ValueError("Stochastic period must be positive")
    result: list[float] = []
    for index in range(len(candles)):
        window = candles[max(0, index - period + 1):index + 1]
        lowest = min(float(candle.low) for candle in window)
        highest = max(float(candle.high) for candle in window)
        spread = highest - lowest
        result.append(50.0 if spread == 0 else (float(candles[index].close) - lowest) * 100.0 / spread)
    return result


def adx(candles: Sequence, period: int = 14) -> list[float]:
    if period < 1:
        raise ValueError("ADX period must be positive")
    if len(candles) < 2:
        return [0.0] * len(candles)
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    true_ranges: list[float] = []
    for index, candle in enumerate(candles):
        if index == 0:
            plus_dm.append(0.0)
            minus_dm.append(0.0)
            true_ranges.append(float(candle.high - candle.low))
            continue
        previous = candles[index - 1]
        up_move = float(candle.high - previous.high)
        down_move = float(previous.low - candle.low)
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        true_ranges.append(max(
            float(candle.high - candle.low),
            abs(float(candle.high - previous.close)),
            abs(float(candle.low - previous.close)),
        ))
    dx: list[float] = []
    for index in range(len(candles)):
        start = max(0, index - period + 1)
        tr = sum(true_ranges[start:index + 1])
        plus_di = 100.0 * sum(plus_dm[start:index + 1]) / tr if tr else 0.0
        minus_di = 100.0 * sum(minus_dm[start:index + 1]) / tr if tr else 0.0
        denominator = plus_di + minus_di
        dx.append(0.0 if denominator == 0 else 100.0 * abs(plus_di - minus_di) / denominator)
    adx_values: list[float] = []
    for index in range(len(dx)):
        window = dx[max(0, index - period + 1):index + 1]
        adx_values.append(sum(window) / len(window))
    return adx_values


def calculate_indicators(candles: Sequence) -> IndicatorSet:
    if len(candles) < 2:
        raise ValueError("At least two completed candles are required")
    closes = [float(candle.close) for candle in candles]
    ema20_values = ema(closes, 20)
    ema50_values = ema(closes, 50)
    ema200_values = ema(closes, 200)
    rsi_values = rsi(closes, 14)
    macd_values, signal_values = macd(closes)
    atr_values = atr(candles, 14)
    upper, lower = bollinger_bands(closes)
    adx_values = adx(candles, 14)
    stochastic_values = stochastic(candles, 14)
    return IndicatorSet(
        ema20=ema20_values[-1], ema50=ema50_values[-1], ema200=ema200_values[-1],
        rsi14=rsi_values[-1], macd=macd_values[-1], macd_signal=signal_values[-1],
        atr14=atr_values[-1], bollinger_upper=upper[-1], bollinger_lower=lower[-1],
        adx=adx_values[-1], stochastic_k=stochastic_values[-1],
    )


def calculate_indicator_history(candles: Sequence) -> list[IndicatorSet]:
    if len(candles) < 2:
        raise ValueError("At least two completed candles are required")
    closes = [float(candle.close) for candle in candles]
    ema20_values = ema(closes, 20)
    ema50_values = ema(closes, 50)
    ema200_values = ema(closes, 200)
    rsi_values = _rsi_prefix_values(closes, 14)
    macd_values, signal_values = macd(closes)
    atr_values = atr(candles, 14)
    upper, lower = bollinger_bands(closes)
    adx_values = adx(candles, 14)
    stochastic_values = stochastic(candles, 14)
    return [
        IndicatorSet(
            ema20=ema20_values[index],
            ema50=ema50_values[index],
            ema200=ema200_values[index],
            rsi14=rsi_values[index],
            macd=macd_values[index],
            macd_signal=signal_values[index],
            atr14=atr_values[index],
            bollinger_upper=upper[index],
            bollinger_lower=lower[index],
            adx=adx_values[index],
            stochastic_k=stochastic_values[index],
        )
        for index in range(len(candles))
    ]
