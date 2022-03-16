# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08

import datetime
import uuid
from enum import IntEnum


class OrderSide(IntEnum):
    BUY = 1  # 股票买入
    SELL = -1  # 股票卖出


class BidType(IntEnum):
    LIMIT = 1  # 限价委托
    MARKET = 2  # 市价委托


class OrderStatus(IntEnum):
    ERROR = -1  # 异常
    NO_DEAL = 1  # 未成交
    PARTIAL_TRANSACTION = 2  # #部分成交
    ALL_TRANSACTIONS = 3  # 全部成交
    CANCEL_ALL_ORDERS = 4  # 全部撤单
    REJECTED = 5  # 已拒绝

    @classmethod
    def get_status(cls, status_cn):
        status_map = {
            "未成交": cls.NO_DEAL.value,
            "部分成交": cls.PARTIAL_TRANSACTION.value,
            "全部成交": cls.ALL_TRANSACTIONS.value,
            "全部撤单": cls.CANCEL_ALL_ORDERS.value,
            "异常": cls.ERROR.value,
        }

        return status_map.get(status_cn)

    def convert(gm_status: int):
        if gm_status == 0 or gm_status == 12 or gm_status == 9:
            return OrderStatus.ERROR
        if gm_status == 1 or gm_status == 10 or gm_status == 6:
            return OrderStatus.NO_DEAL
        if gm_status == 2:
            return OrderStatus.PARTIAL_TRANSACTION
        if gm_status == 3:
            return OrderStatus.ALL_TRANSACTIONS
        if gm_status == 5:
            return OrderStatus.CANCEL_ALL_ORDERS
        if gm_status == 8:
            return OrderStatus.REJECTED

        return OrderStatus.ERROR


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


class TradeOrder:
    # 逐笔成交的记录，用于汇总计算

    def __init__(
        self,
        eid: str,
        price: float,
        filled: int,
        create_at: datetime.datetime,
        recv_at: datetime.datetime,
    ):
        self.eid = eid
        self.price = price
        self.filled = filled
        self.create_at = create_at
        self.recv_at = recv_at


class TradeEvent:
    # 委托结果，包括了成功和失败的集合

    def __init__(
        self,
        symbol: str,
        price: float,
        volume: int,
        order_side: int,
        bid_type: int,
        create_at: datetime.datetime,
        sid: str,
        status: int,
        avg_price: float,
        filled: int,
        order_id: str,
        trade_fees: float,
        reason: str,
        recv_at: datetime.datetime,
    ):
        self.code = symbol
        self.price = price
        self.volume = volume
        self.order_side = order_side
        self.bid_type = bid_type
        self.create_at = create_at.strftime("%Y-%m-%d %H:%M:%S.%f")
        self.entrust_no = sid
        self.status = OrderStatus.convert(status)
        self.avg_price = avg_price  # 此价格计算方式待定
        self.filled = filled
        self.order_id = order_id
        self.reason = reason
        self.trade_fees = trade_fees
        self.recv_at = recv_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    def toDict(self):
        return {
            "code": self.code,
            "price": self.price,
            "volume": self.volume,
            "order_side": self.order_side,
            "bid_type": self.bid_type,
            "time": self.create_at,
            "entrust_no": self.entrust_no,
            "status": self.status,
            "average_price": self.avg_price,
            "filled": self.filled,
            "eid": self.order_id,
            "trade_fees": self.trade_fees,
            "reason": self.reason,
            "recv_at": self.recv_at,
        }
