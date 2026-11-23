from datetime import UTC, datetime
from decimal import Decimal


class SignalValidationError(ValueError):
    pass


def validate_signal(signal, minimum_reward_risk: Decimal = Decimal("2"), now: datetime | None = None) -> None:
    if signal.direction not in {"BUY", "SELL"}:
        raise SignalValidationError("Signal direction must be BUY or SELL")
    if signal.quality_score < 0 or signal.quality_score > 100:
        raise SignalValidationError("Signal quality score must be between 0 and 100")

    entry = Decimal(str(signal.entry))
    stop = Decimal(str(signal.stop_loss))
    targets = [Decimal(str(value)) for value in (signal.take_profit_1, signal.take_profit_2, signal.take_profit_3)]
    if entry <= 0 or stop <= 0:
        raise SignalValidationError("Entry and stop loss must be positive")

    if signal.direction == "BUY":
        if stop >= entry:
            raise SignalValidationError("BUY stop loss must be below entry")
        if any(target <= entry for target in targets):
            raise SignalValidationError("BUY take-profit targets must be above entry")
        risk = entry - stop
        rewards = [target - entry for target in targets]
    else:
        if stop <= entry:
            raise SignalValidationError("SELL stop loss must be above entry")
        if any(target >= entry for target in targets):
            raise SignalValidationError("SELL take-profit targets must be below entry")
        risk = stop - entry
        rewards = [entry - target for target in targets]

    if risk <= 0:
        raise SignalValidationError("Protective stop loss is invalid")
    if rewards[-1] / risk < minimum_reward_risk:
        raise SignalValidationError("Minimum 1:2 reward/risk target is not met")
