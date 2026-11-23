from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class StrategySignal:
    strategy: str
    direction: str
    timeframe: str
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    quality_score: int
    explanation: str


class Strategy(ABC):
    name: str

    @abstractmethod
    def evaluate(self, symbol: str, timeframe: str, candles: Sequence, context: Mapping | None = None) -> StrategySignal | None:
        """Evaluate only completed candles and return an unexecuted signal."""
