import uuid
from enum import IntEnum


class OrderSide(IntEnum):
    BUY = 1
    SELL = -1

    def __str__(self):
        return {OrderSide.BUY: "买入", OrderSide.SELL: "卖出"}[self]


class BidType(IntEnum):
    LIMIT = 1
    MARKET = 2

    def __str__(self):
        return {
            BidType.LIMIT: "限价委托",
            BidType.MARKET: "市价委托",
        }


class Order:
    def __init__(
        self,
        security: str,
        side: OrderSide,
        volume: int,
        price: float = None,
        bid_type: BidType = BidType.MARKET,
    ):
        self.security = security
        self.side = side
        self.volume = volume
        self.price = price
        self.bid_type = bid_type

        self.oid = uuid.uuid4()


class Trade:
    def __init__(self, order: Order, price: float, volume: int):
        self.order = order
        self.price = price
        self.volume = volume
        self.tid = uuid.uuid4()


class EntrustError(IntEnum):
    SUCCESS = 0
    FAILED_GENERIC = -1
    FAILED_NOT_ENOUGH_CASH = -2
    REACH_BUY_LIMIT = -3
    REACH_SELL_LIMIT = -4

    def __str__(self):
        return {
            EntrustError.SUCCESS: "成功委托",
            EntrustError.FAILED_GENERIC: "委托失败",
            EntrustError.FAILED_NOT_ENOUGH_CASH: "资金不足",
            EntrustError.REACH_BUY_LIMIT: "不能在涨停板上买入",
            EntrustError.REACH_SELL_LIMIT: "不能在跌停板上卖出",
        }.get(self)
