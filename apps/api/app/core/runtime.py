from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class RuntimeState:
    broker: str = "none"
    environment: str = "demo"
    account_id: str = ""
    server: str = ""
    mt5_connected: bool = False
    engine_running: bool = False
    live_trading_enabled: bool = False
    message: str = "No broker connected"
    encrypted_credentials: str | None = None
    account_currency: str = ""
    balance: Decimal | None = None
    equity: Decimal | None = None
    market_data: tuple[dict, ...] = ()
    worker_last_seen: datetime | None = None


class RuntimeStateStore:
    def __init__(self) -> None:
        self.state = RuntimeState()

    def connect_demo(self) -> RuntimeState:
        self.state = replace(
            self.state,
            broker="simulation",
            environment="demo",
            account_id="SIM-DEMO-001",
            server="Simulation",
            mt5_connected=True,
            encrypted_credentials=None,
            account_currency="USD",
            balance=Decimal("10000"),
            equity=Decimal("10000"),
            market_data=(),
            worker_last_seen=None,
            message="Simulation demo account connected",
        )
        return self.state

    def disconnect(self) -> RuntimeState:
        self.state = replace(
            self.state,
            broker="none",
            environment="demo",
            account_id="",
            server="",
            mt5_connected=False,
            engine_running=False,
            encrypted_credentials=None,
            account_currency="",
            balance=None,
            equity=None,
            market_data=(),
            worker_last_seen=None,
            message="Broker disconnected",
        )
        return self.state

    def configure_mt5_account(
        self,
        account_id: str,
        server: str,
        environment: str,
        encrypted_credentials: str,
    ) -> RuntimeState:
        self.state = replace(
            self.state,
            broker="mt5",
            environment=environment,
            account_id=account_id,
            server=server,
            mt5_connected=False,
            engine_running=False,
            encrypted_credentials=encrypted_credentials,
            account_currency="",
            balance=None,
            equity=None,
            market_data=(),
            worker_last_seen=None,
            message=f"MT5 {environment} credentials queued for {server}; waiting for the Windows worker",
        )
        return self.state

    def claim_mt5_credentials(self) -> str | None:
        if self.state.broker != "mt5":
            return None
        encrypted = self.state.encrypted_credentials
        if encrypted:
            self.state = replace(self.state, encrypted_credentials=None)
        return encrypted

    def update_mt5_status(
        self,
        *,
        connected: bool,
        account_id: str,
        server: str,
        environment: str,
        message: str,
        currency: str = "",
        balance: Decimal | None = None,
        equity: Decimal | None = None,
        market_data: list[dict] | None = None,
    ) -> RuntimeState:
        if (
            self.state.broker != "mt5"
            or self.state.account_id != account_id
            or self.state.environment != environment
        ):
            raise ValueError("Worker status does not match the configured MT5 account")
        self.state = replace(
            self.state,
            mt5_connected=connected,
            server=server,
            account_currency=currency,
            balance=balance,
            equity=equity,
            market_data=tuple(market_data or ()),
            worker_last_seen=datetime.now(UTC),
            engine_running=self.state.engine_running if connected else False,
            message=message,
        )
        return self.state

    def broker_connected(self) -> bool:
        state = self.state
        if not state.mt5_connected:
            return False
        if state.broker != "mt5":
            return True
        return (
            state.worker_last_seen is not None
            and datetime.now(UTC) - state.worker_last_seen <= timedelta(seconds=15)
        )

    def start_engine(self) -> RuntimeState:
        if self.state.broker == "mt5" and self.state.environment == "live":
            self.state = replace(
                self.state,
                engine_running=False,
                message="Live MT5 account is read-only; trading remains disabled",
            )
            return self.state
        if not self.broker_connected():
            return replace(self.state, engine_running=False, message="Engine stopped: broker is disconnected")
        self.state = replace(self.state, engine_running=True, message="Trading engine running")
        return self.state

    def stop_engine(self) -> RuntimeState:
        self.state = replace(self.state, engine_running=False, message="Trading engine stopped")
        return self.state


runtime_store = RuntimeStateStore()
