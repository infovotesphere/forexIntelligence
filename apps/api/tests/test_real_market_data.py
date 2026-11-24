from datetime import UTC, datetime
from unittest.mock import Mock

from app.core import real_market_data


def test_crypto_symbol_resolves_to_usd_market_data(monkeypatch):
    observed = {}
    timestamp = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
    response = Mock()
    response.json.return_value = {
        "chart": {
            "result": [{
                "timestamp": [timestamp],
                "indicators": {
                    "quote": [{
                        "open": [95000.0],
                        "high": [95100.0],
                        "low": [94900.0],
                        "close": [95050.0],
                        "volume": [1000],
                    }],
                },
            }],
        },
    }

    def fake_get(url, **kwargs):
        observed["url"] = url
        observed.update(kwargs)
        return response

    monkeypatch.setattr(real_market_data, "_cache", {})
    monkeypatch.setattr(real_market_data.httpx, "get", fake_get)

    candles = real_market_data.get_real_market_candles("BTCUSD", "H1")

    assert observed["url"].endswith("/BTC-USD")
    assert candles[0].symbol == "BTCUSD"
    assert str(candles[0].close) == "95050.0"


def test_one_minute_market_data_requests_only_supported_seven_day_window(monkeypatch):
    observed = {}
    timestamp = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
    response = Mock()
    response.json.return_value = {
        "chart": {
            "result": [{
                "timestamp": [timestamp],
                "indicators": {
                    "quote": [{
                        "open": [1.1],
                        "high": [1.101],
                        "low": [1.099],
                        "close": [1.1005],
                        "volume": [100],
                    }],
                },
            }],
        },
    }

    def fake_get(url, **kwargs):
        observed["url"] = url
        observed.update(kwargs)
        return response

    monkeypatch.setattr(real_market_data, "_cache", {})
    monkeypatch.setattr(real_market_data.httpx, "get", fake_get)

    candles = real_market_data.get_real_market_candles("EURUSD", "M1")

    assert observed["params"] == {"interval": "1m", "range": "7d"}
    assert candles[0].timeframe == "M1"
