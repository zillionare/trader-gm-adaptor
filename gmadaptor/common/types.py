# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08

import datetime
from enum import IntEnum


class OrderSide(IntEnum):
    BUY = 1  # 股票买入
    SELL = -1  # 股票卖出

    def convert(order_side: int):
        if order_side == 1:
            return OrderSide.BUY
        if order_side == 2:
            return OrderSide.SELL
        else:
            return None


class OrderType(IntEnum):
    LIMIT = 1  # 限价委托
    MARKET = 2  # 市价委托

    def convert(order_type: int):
        if order_type == 1:
            return OrderType.LIMIT
        if order_type == 24:
            return OrderType.MARKET
        else:
            return None


class OrderStatus(IntEnum):
    ERROR = -1  # 异常
    RECEIVED = 0  # 已接收
    SUBMITTED = 1  # 已报
    PARTIAL_TX = 2  # #部分成交
    ALL_TX = 3  # 全部成交
    CANCELED = 4  # 撤单

    def convert(gm_status: int):
        # 未知，挂起，已拒绝
        if gm_status == 0 or gm_status == 9 or gm_status == 8:
            return OrderStatus.ERROR
        # 已报，待报，待撤
        if gm_status == 1 or gm_status == 10 or gm_status == 6:
            return OrderStatus.SUBMITTED
        # 部分成交
        if gm_status == 2:
            return OrderStatus.PARTIAL_TX
        # 全部成交
        if gm_status == 3:
            return OrderStatus.ALL_TX
        # 已撤，或者已过期
        if gm_status == 5 or gm_status == 12:
            return OrderStatus.CANCELED

        return OrderStatus.ERROR


class TradeOrder:
    symbol: str  # 股票代码
    price: float  # 交易价格
    volume: int  # 交易量
    order_side: OrderSide  # 买入或者卖出
    order_type: OrderType  # 限价或者市价
    timeout_left: float  # 操作剩余的超时毫秒数

    # 支持一次多笔买入或者卖出操作，不能市价和限价混合买入卖出
    def __init__(
        self,
        security: str,
        price: float,
        volume: int,
        order_side: OrderSide,
        order_type: OrderType,
        timeout: float,
    ):
        self.symbol = security
        self.price = price
        self.volume = volume
        self.order_side = order_side
        self.order_type = order_type
        self.timeout_left = timeout


class TradeEvent:
    # 委托结果，包括了成功和失败的集合

    def __init__(
        self,
        symbol: str,
        price: float,
        volume: int,
        order_side: int,
        bid_type: int,
        created_at: datetime.datetime,
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
        self.created_at = created_at
        self.entrust_no = sid
        self.status = status
        self.avg_price = avg_price
        self.filled = filled
        self.order_id = order_id
        self.reason = reason
        self.trade_fees = trade_fees
        self.recv_at = recv_at
        self.filled_amount = 0
        self.invalid = False

    def toDict(self):
        return {
            "code": self.code,
            "price": self.price,
            "volume": self.volume,
            "order_side": self.order_side,
            "bid_type": self.bid_type,
            "time": self.created_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "entrust_no": self.entrust_no,
            "status": self.status,
            "average_price": self.avg_price,
            "filled": self.filled,
            "filled_amount": self.filled_amount,
            "eid": self.order_id,
            "trade_fees": self.trade_fees,
            "reason": self.reason,
            "recv_at": self.recv_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
        }
