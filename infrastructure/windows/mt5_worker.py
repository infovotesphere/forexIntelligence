import logging
import os
from pathlib import Path
import sys
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading.connectors.mt5 import MT5Adapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("forex-mt5-worker")
MONITORED_SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD")
TIMEFRAME_MINUTES = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
CANDLE_HISTORY_BARS = 260
CANDLE_REFRESH_SECONDS = 60


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be configured")
    return value


def collect_market_candles(adapter: MT5Adapter, market_data: list[dict]) -> list[dict]:
    end = datetime.now(UTC)
    snapshots = []
    for quote in market_data:
        symbol = quote["symbol"]
        for timeframe, minutes in TIMEFRAME_MINUTES.items():
            start = end - timedelta(minutes=minutes * CANDLE_HISTORY_BARS)
            try:
                candles = adapter.get_historical_candles(symbol, timeframe, start, end)
            except RuntimeError as exc:
                logger.warning("MT5 candle history unavailable for %s %s: %s", symbol, timeframe, exc)
                continue
            if len(candles) < 2:
                continue
            snapshots.append({
                "base_symbol": quote["base_symbol"],
                "symbol": symbol,
                "timeframe": timeframe,
                "candles": [
                    {
                        "time": candle.time.isoformat(),
                        "open": str(candle.open),
                        "high": str(candle.high),
                        "low": str(candle.low),
                        "close": str(candle.close),
                        "volume": str(candle.volume),
                    }
                    for candle in candles[-CANDLE_HISTORY_BARS:]
                ],
            })
    return snapshots


def main() -> None:
    api_url = required_setting("FOREX_INTELLIGENCE_API_URL").rstrip("/")
    worker_token = required_setting("MT5_WORKER_TOKEN")
    parsed = urlparse(api_url)
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("The remote backend URL must use HTTPS")

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {worker_token}"})
    adapter: MT5Adapter | None = None
    credentials: dict | None = None
    last_candle_refresh = 0.0
    pending_market_candles: list[dict] = []

    while True:
        try:
            if credentials is None:
                response = session.post(f"{api_url}/api/v1/worker/mt5/claim", timeout=15)
                if response.status_code == 204:
                    time.sleep(3)
                    continue
                response.raise_for_status()
                credentials = response.json()
                adapter = MT5Adapter(
                    login=int(credentials["account_id"]),
                    password=credentials["password"],
                    server=credentials["server"],
                    environment=credentials["environment"],
                )
                last_candle_refresh = 0.0
                pending_market_candles = []
                logger.info(
                    "Received MT5 %s connection request for account %s",
                    credentials["environment"],
                    credentials["account_id"],
                )

            if adapter is None:
                raise RuntimeError("MT5 adapter was not initialized")
            if not adapter.connection_status()["connected"] and not adapter.connect():
                error = adapter.last_error()
                raise ConnectionError(f"MT5 terminal login failed: {error}")

            account = adapter.get_account_info()
            market_data = adapter.get_monitored_quotes(MONITORED_SYMBOLS)
            if time.monotonic() - last_candle_refresh >= CANDLE_REFRESH_SECONDS:
                pending_market_candles = collect_market_candles(adapter, market_data)
                last_candle_refresh = time.monotonic()
            open_positions = adapter.get_open_positions()
            history_deals = adapter.get_deal_history(
                datetime.now(UTC) - timedelta(days=30),
                datetime.now(UTC),
            )[-500:]
            status_response = session.post(
                f"{api_url}/api/v1/worker/mt5/status",
                json={
                    "connected": True,
                    "account_id": account.account_id,
                    "server": credentials["server"],
                    "currency": account.currency,
                    "balance": str(account.balance),
                    "equity": str(account.equity),
                    "market_data": market_data,
                    "market_candles": pending_market_candles,
                    "open_positions": open_positions,
                    "history_deals": history_deals,
                    "environment": credentials["environment"],
                    "message": f"MT5 {credentials['environment']} connected; trading remains paper-only",
                },
                timeout=15,
            )
            status_response.raise_for_status()
            pending_market_candles = []
            time.sleep(5)
        except (requests.RequestException, ConnectionError, PermissionError, RuntimeError, ValueError, KeyError) as exc:
            logger.error("MT5 worker connection/status error: %s", exc)
            if credentials is not None:
                try:
                    failed = session.post(
                        f"{api_url}/api/v1/worker/mt5/status",
                        json={
                            "connected": False,
                            "account_id": credentials["account_id"],
                            "server": credentials["server"],
                            "environment": credentials["environment"],
                            "message": str(exc)[:500],
                        },
                        timeout=15,
                    )
                    failed.raise_for_status()
                except requests.RequestException as status_error:
                    logger.error("Could not report MT5 worker status: %s", status_error)
            if adapter is not None:
                adapter.disconnect()
                adapter = None
            credentials = None
            time.sleep(5)


if __name__ == "__main__":
    main()
