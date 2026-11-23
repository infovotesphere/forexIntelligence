from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.broker import simulation_adapter
from app.core.market_data import get_mt5_candles
from app.core.database import get_db
from app.core.runtime import runtime_store
from app.models.trading_signal import TradingSignal
from trading.signals.generator import generate_validated_signals
from trading.strategies.trend_following import TrendFollowingStrategy
from trading.strategies.breakout_retest import BreakoutRetestStrategy

router = APIRouter(prefix="/signals", tags=["signals"])
signal_store: list[dict] = []
realtime_state: dict = {
    "enabled": True,
    "interval_seconds": 30,
    "last_scan_at": None,
    "last_scan_error": None,
}
TIMEFRAME_MINUTES = {"M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
SUPPORTED_TIMEFRAMES = tuple(TIMEFRAME_MINUTES)
REALTIME_SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD")


@router.get("/realtime/status")
def realtime_status() -> dict:
    return {
        **realtime_state,
        "connected": runtime_store.broker_connected(),
        "history_count": len(signal_store),
    }


@router.get("/")
@router.get("")
def list_signals(status: str | None = None, db: Session = Depends(get_db)) -> dict:
    now = datetime.now(UTC)
    items = []
    persisted = db.scalars(select(TradingSignal).order_by(TradingSignal.created_at.desc()).limit(1000)).all()
    persisted_ids = set()
    for row in persisted:
        item = dict(row.payload)
        item.setdefault("signal_id", row.signal_id)
        item.setdefault("symbol", row.symbol)
        item.setdefault("timeframe", row.timeframe)
        item.setdefault("strategy", row.strategy)
        item.setdefault("status", row.status)
        item.setdefault("simulated", row.simulated)
        item.setdefault("data_source", row.data_source)
        item.setdefault("created_at", row.created_at.isoformat())
        item.setdefault("expires_at", row.expires_at.isoformat())
        item["status"] = "EXPIRED" if item["status"] == "VALIDATED" and row.expires_at <= now else item["status"]
        persisted_ids.add(row.signal_id)
        if status is None or item["status"] == status.upper():
            items.append(item)

    for signal in signal_store:
        item = dict(signal)
        if item["status"] == "VALIDATED" and item.get("expires_at"):
            expires_at = datetime.fromisoformat(item["expires_at"])
            if expires_at <= now:
                item["status"] = "EXPIRED"
        if item.get("signal_id") not in persisted_ids and (status is None or item["status"] == status.upper()):
            items.append(item)
    return {"items": items, "total": len(items), "page": 1, "page_size": 100}


@router.post("/generate")
def generate_signals(
    symbol: str = Query(min_length=1),
    timeframe: str = Query(default="H1", pattern="^(M5|M15|M30|H1|H4|D1|ALL)$"),
    db: Session = Depends(get_db),
) -> dict:
    scan_all = timeframe == "ALL"
    timeframes = SUPPORTED_TIMEFRAMES if scan_all else (timeframe,)
    simulated = runtime_store.state.broker != "mt5"
    generated: list[dict] = []
    scanned_timeframes: list[str] = []
    unavailable_timeframes: list[str] = []
    rejected_candidates = 0

    if not simulated and not runtime_store.broker_connected():
        raise HTTPException(
            status_code=503,
            detail="MT5 worker is disconnected; refusing to substitute simulation candles",
        )

    for scan_timeframe in timeframes:
        actual_symbol = symbol.upper()
        try:
            if not simulated:
                snapshot = get_mt5_candles(symbol.upper(), scan_timeframe)
                if snapshot is None:
                    if scan_all:
                        unavailable_timeframes.append(scan_timeframe)
                        continue
                    raise HTTPException(
                        status_code=503,
                        detail=f"No MT5 {scan_timeframe} candle history is available for {symbol.upper()}",
                    )
                actual_symbol, candles = snapshot
                quote = next(
                    (
                        item for item in runtime_store.state.market_data
                        if str(item.get("base_symbol") or "").upper() == symbol.upper()
                        or str(item.get("symbol") or "").upper() == actual_symbol.upper()
                    ),
                    None,
                )
                if quote is None:
                    raise HTTPException(status_code=503, detail=f"No MT5 quote metadata is available for {actual_symbol}")
                try:
                    tick_size = Decimal(str(quote["tick_size"]))
                except (KeyError, InvalidOperation) as exc:
                    raise HTTPException(status_code=503, detail=f"MT5 tick size is unavailable for {actual_symbol}") from exc
                if not tick_size.is_finite() or tick_size <= 0:
                    raise HTTPException(status_code=503, detail=f"MT5 tick size is invalid for {actual_symbol}")
            else:
                end = datetime.now(UTC)
                minutes = TIMEFRAME_MINUTES[scan_timeframe]
                candles = simulation_adapter.get_historical_candles(
                    symbol.upper(), scan_timeframe, end - timedelta(minutes=minutes * 260), end
                )
                tick_size = simulation_adapter.get_symbol_info(actual_symbol).tick_size
        except HTTPException:
            raise
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        candidates = generate_validated_signals(
            actual_symbol, scan_timeframe, candles,
            [TrendFollowingStrategy(), BreakoutRetestStrategy()],
            tick_size=tick_size,
        )
        scanned_timeframes.append(scan_timeframe)
        for signal in candidates:
            signal["simulated"] = simulated
            signal["data_source"] = "simulation" if simulated else "mt5"
        rejected_candidates += sum(signal.get("status") == "REJECTED" for signal in candidates)
        generated.extend(signal for signal in candidates if signal.get("status") == "VALIDATED")

    if scan_all and not scanned_timeframes:
        source = "MT5" if not simulated else "simulation"
        raise HTTPException(
            status_code=503,
            detail=f"No {source} candle history is available for {symbol.upper()} in any supported timeframe",
        )

    for generated_signal in generated:
        existing_ids = {item.get("signal_id") for item in signal_store}
        if generated_signal.get("signal_id") not in existing_ids:
            signal_store.append(generated_signal)

        signal_id = generated_signal["signal_id"]
        existing = db.scalar(select(TradingSignal).where(TradingSignal.signal_id == signal_id))
        if existing is None:
            created_at_text = generated_signal.get("created_at")
            expires_at_text = generated_signal.get("expires_at")
            created_at = datetime.fromisoformat(created_at_text) if created_at_text else datetime.now(UTC)
            expires_at = datetime.fromisoformat(expires_at_text) if expires_at_text else created_at + timedelta(hours=4)
            db.add(TradingSignal(
                signal_id=signal_id,
                symbol=generated_signal["symbol"],
                timeframe=generated_signal["timeframe"],
                strategy=generated_signal.get("strategy", "Unknown"),
                status="VALIDATED",
                simulated=generated_signal.get("simulated", simulated),
                data_source=generated_signal.get("data_source", "simulation" if simulated else "mt5"),
                created_at=created_at,
                expires_at=expires_at,
                payload=generated_signal,
            ))
    db.commit()
    if len(signal_store) > 1000:
        del signal_store[:-1000]
    return {
        "items": generated,
        "total": len(generated),
        "simulated": simulated,
        "data_source": "simulation" if simulated else "mt5",
        "scanned_timeframes": scanned_timeframes,
        "unavailable_timeframes": unavailable_timeframes,
        "rejected_candidates": rejected_candidates,
    }
