import pytest
from types import SimpleNamespace

from trading.connectors.mt5 import MT5Adapter


def test_mt5_adapter_never_submits_or_modifies_broker_orders():
    adapter = object.__new__(MT5Adapter)
    with pytest.raises(PermissionError, match="Paper-trading mode"):
        adapter.submit_order("EURUSD", "BUY", 0.01, stop_loss=1.0)
    with pytest.raises(PermissionError, match="does not modify"):
        adapter.modify_position("ticket", stop_loss=1.0)
    with pytest.raises(PermissionError, match="does not close"):
        adapter.close_position("ticket")


def test_mt5_trade_mode_check_uses_selected_environment():
    adapter = object.__new__(MT5Adapter)
    adapter._environment = "live"
    adapter._mt5 = SimpleNamespace(ACCOUNT_TRADE_MODE_DEMO=0, ACCOUNT_TRADE_MODE_REAL=2)
    assert adapter._expected_trade_mode() == 2
    adapter._environment = "demo"
    assert adapter._expected_trade_mode() == 0
