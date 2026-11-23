from decimal import Decimal, ROUND_DOWN

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.broker import simulation_adapter
from app.core.config import get_settings
from app.core.runtime import runtime_store

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/policy")
def get_risk_policy() -> dict:
    settings = get_settings()
    return {
        "max_risk_per_trade_percent": "1",
        "max_daily_loss_percent": str(settings.max_daily_loss_percent),
        "max_weekly_loss_percent": str(settings.max_weekly_loss_percent),
        "max_simultaneous_positions": settings.max_simultaneous_positions,
        "max_aggregate_open_risk_percent": str(settings.max_aggregate_open_risk_percent),
        "martingale_allowed": False,
        "grid_allowed": False,
        "live_trading_enabled": settings.live_trading_enabled,
    }


class PositionSizeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32, pattern="^[A-Za-z0-9._-]+$")
    entry: Decimal = Field(gt=0)
    stop_loss: Decimal = Field(gt=0)
    risk_percent: Decimal = Field(default=Decimal("1"), gt=0, le=1)


@router.post("/position-size")
def calculate_position_size(payload: PositionSizeRequest) -> dict:
    if not runtime_store.broker_connected():
        raise HTTPException(status_code=409, detail="Connect a broker account before calculating position size")
    if runtime_store.state.broker != "simulation":
        raise HTTPException(
            status_code=501,
            detail="Position sizing for MT5 requires broker symbol specifications from the Windows worker",
        )

    try:
        instrument = simulation_adapter.get_symbol_info(payload.symbol.upper())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not instrument.trade_allowed:
        raise HTTPException(status_code=422, detail=f"Trading is not allowed for {instrument.symbol}")

    equity = runtime_store.state.equity
    if equity is None or equity <= 0:
        raise HTTPException(status_code=409, detail="Connected account equity is unavailable")

    price_distance = abs(payload.entry - payload.stop_loss)
    risk_amount = equity * payload.risk_percent / Decimal("100")
    loss_per_lot = price_distance / instrument.tick_size * instrument.tick_value
    if loss_per_lot <= 0:
        raise HTTPException(status_code=422, detail="Entry and stop loss must have a positive distance")

    raw_volume = risk_amount / loss_per_lot
    stepped_volume = (raw_volume / instrument.volume_step).to_integral_value(rounding=ROUND_DOWN) * instrument.volume_step
    volume = min(stepped_volume, instrument.maximum_volume)
    if volume < instrument.minimum_volume:
        volume = Decimal("0")
    estimated_risk = volume * loss_per_lot

    return {
        "symbol": instrument.symbol,
        "entry": str(payload.entry),
        "stop_loss": str(payload.stop_loss),
        "price_distance": str(price_distance),
        "account_equity": str(equity),
        "risk_percent": str(payload.risk_percent),
        "risk_budget": str(risk_amount),
        "volume": str(volume),
        "volume_step": str(instrument.volume_step),
        "estimated_risk": str(estimated_risk),
        "risk_within_budget": estimated_risk <= risk_amount,
        "reason": (
            "Calculated volume is below the broker minimum; no safe position size is available"
            if volume == 0
            else None
        ),
        "simulated": True,
        "trading_mode": "paper_only",
    }
