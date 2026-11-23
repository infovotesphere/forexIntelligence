from enum import Enum


class TradingEnvironment(str, Enum):
    DEMO = "demo"
    LIVE = "live"
    SIMULATION = "simulation"


class OrderDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class BrokerType(str, Enum):
    MT5 = "mt5"
    SIMULATION = "simulation"
