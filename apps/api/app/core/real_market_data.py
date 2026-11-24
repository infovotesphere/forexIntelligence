from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from threading import Lock

import httpx

from shared.contracts.broker import Candle


YAHOO_SYMBOLS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "USDCHF": "USDCHF=X",
    "USDCAD": "USDCAD=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X",
    "EURGBP": "EURGBP=X",
    "EURJPY": "EURJPY=X",
    "EURAUD": "EURAUD=X",
    "EURCAD": "EURCAD=X",
    "EURCHF": "EURCHF=X",
    "EURNZD": "EURNZD=X",
    "GBPJPY": "GBPJPY=X",
    "GBPAUD": "GBPAUD=X",
    "GBPCAD": "GBPCAD=X",
    "GBPCHF": "GBPCHF=X",
    "GBPNZD": "GBPNZD=X",
    "AUDJPY": "AUDJPY=X",
    "AUDCAD": "AUDCAD=X",
    "AUDNZD": "AUDNZD=X",
    "AUDCHF": "AUDCHF=X",
    "CADJPY": "CADJPY=X",
    "CADCHF": "CADCHF=X",
    "CHFJPY": "CHFJPY=X",
    "NZDJPY": "NZDJPY=X",
    "NZDCAD": "NZDCAD=X",
    "NZDCHF": "NZDCHF=X",
    "XAUUSD": "GC=F",
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
    "BNBUSD": "BNB-USD",
    "SOLUSD": "SOL-USD",
    "XRPUSD": "XRP-USD",
    "ADAUSD": "ADA-USD",
    "DOGEUSD": "DOGE-USD",
    "LTCUSD": "LTC-USD",
    "BCHUSD": "BCH-USD",
    "AVAXUSD": "AVAX-USD",
}
YAHOO_INTERVALS = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "M30": "30m",
    "H1": "60m",
    "H4": "60m",
    "D1": "1d",
}
_cache: dict[tuple[str, str], tuple[datetime, list[Candle]]] = {}
_cache_lock = Lock()


def get_real_market_candles(
    symbol: str,
    timeframe: str,
    *,
    cache_ttl: timedelta = timedelta(minutes=5),
) -> list[Candle]:
    normalized_symbol = symbol.upper()
    yahoo_symbol = YAHOO_SYMBOLS.get(normalized_symbol)
    interval = YAHOO_INTERVALS.get(timeframe)
    if yahoo_symbol is None:
        raise KeyError(f"Unsupported real-market symbol: {normalized_symbol}")
    if interval is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    cache_key = (normalized_symbol, timeframe)
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and datetime.now(UTC) - cached[0] < cache_ttl:
            return list(cached[1])

    range_value = "7d" if timeframe == "M1" else "60d" if timeframe in {"M5", "M15", "M30", "H1", "H4"} else "2y"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    try:
        response = httpx.get(
            url,
            params={"interval": interval, "range": range_value},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("Real market candle provider unavailable") from exc

    try:
        result = payload["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Real market candle provider returned no chart data") from exc

    candles: list[Candle] = []
    for index, timestamp in enumerate(timestamps):
        try:
            open_price = quote["open"][index]
            high = quote["high"][index]
            low = quote["low"][index]
            close = quote["close"][index]
            volume = quote["volume"][index] if quote.get("volume") else None
            if None in (open_price, high, low, close):
                continue
            candles.append(Candle(
                symbol=normalized_symbol,
                timeframe=timeframe,
                time=datetime.fromtimestamp(timestamp, UTC),
                open=Decimal(str(open_price)),
                high=Decimal(str(high)),
                low=Decimal(str(low)),
                close=Decimal(str(close)),
                volume=Decimal(str(volume or 0)),
            ))
        except (InvalidOperation, TypeError, ValueError):
            continue

    if not candles:
        raise RuntimeError("Real market candle provider returned no valid OHLC candles")

    if timeframe == "H4":
        candles = _aggregate_candles(candles, normalized_symbol, timeframe, 240)

    with _cache_lock:
        _cache[cache_key] = (datetime.now(UTC), candles)
    return list(candles)


def _aggregate_candles(candles: list[Candle], symbol: str, timeframe: str, minutes: int) -> list[Candle]:
    grouped: dict[datetime, list[Candle]] = {}
    interval = timedelta(minutes=minutes)
    for candle in candles:
        bucket = datetime.fromtimestamp(int(candle.time.timestamp() // interval.total_seconds()) * int(interval.total_seconds()), UTC)
        grouped.setdefault(bucket, []).append(candle)

    aggregated: list[Candle] = []
    for bucket in sorted(grouped):
        group = grouped[bucket]
        aggregated.append(Candle(
            symbol=symbol,
            timeframe=timeframe,
            time=bucket,
            open=group[0].open,
            high=max(candle.high for candle in group),
            low=min(candle.low for candle in group),
            close=group[-1].close,
            volume=sum((candle.volume for candle in group), Decimal("0")),
        ))
    return aggregated
