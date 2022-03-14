# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08

import uuid
from enum import IntEnum


"""order_biz 委托业务类型
股票
    1	股票, 买入
    2	股票, 卖出
期货
    10	期货, 买入开仓
    11	期货, 卖出平仓
    12	期货, 卖出平仓, 平今仓 (上海商品期货交易所 only)
    13	期货, 卖出平仓, 平昨仓 (上海商品期货交易所 only)
    14	期货, 卖出开仓
    15	期货, 买入平仓
    16	期货, 买入平仓，平今仓 (上海商品期货交易所 only)
    17	期货, 买入平仓, 平昨仓 (上海商品期货交易所 only)
"""


class OrderBiz(IntEnum):
    BUY = 1
    SELL = 2


"""
order_type 委托类型
深圳市场
    1	限价
    20	市价, 对方最优价格 (best of counterparty)
    21	市价, 己方最优价格 (best of party)
    22	市价, 即时成交剩余撤销 (fill and kill)
    23	市价, 即时全额成交或撤销 (fill or kill)
    24	市价, 最优五档剩余撤销 (best 5 then cancel)
上海市场
    1	限价
    24	市价, 最优五档剩余撤销 (best 5 then cancel)
    25	市价, 最优五档剩余转限价(best 5 then limit)
"""


class OrderType(IntEnum):
    LIMITPRICE = 1
    FILLANDKILL = 22
    FILLORKILL = 23
    BESTCANCEL = 24
    BESTLIMIT = 25


"""ExecType - 执行回报类型
ExecType_Unknown = 0
ExecType_New = 1                      # 已报
ExecType_Canceled = 5                 # 已撤销
ExecType_PendingCancel = 6            # 待撤销
ExecType_Rejected = 8                 # 已拒绝
ExecType_Suspended = 9                # 挂起
ExecType_PendingNew = 10              # 待报
ExecType_Expired = 12                 # 过期
ExecType_Trade = 15                   # 成交   (有效)
ExecType_OrderStatus = 18             # 委托状态
ExecType_CancelRejected = 19          # 撤单被拒绝  (有效)
"""


class ExecType(IntEnum):
    UNKNOWN = 0
    NEW = 1
    CANCELED = 5
    PENDINGCANCEL = 6
    REJECTED = 8
    SUSPENDED = 9
    PENDINGNEW = 10
    EXPIRED = 12
    TRADE = 15
    ORDERSTATUS = 18
    CANCELREJECTED = 19


"""OrderStatus - 委托状态
OrderStatus_Unknown = 0
OrderStatus_New = 1                   # 已报
OrderStatus_PartiallyFilled = 2       # 部成
OrderStatus_Filled = 3                # 已成
OrderStatus_Canceled = 5              # 已撤
OrderStatus_PendingCancel = 6         # 待撤
OrderStatus_Rejected = 8              # 已拒绝
OrderStatus_Suspended = 9             # 挂起 （无效）
OrderStatus_PendingNew = 10           # 待报
OrderStatus_Expired = 12              # 已过期
"""


class OrderStatus(IntEnum):
    UNKNOWN = 0
    NEW = 1
    PARTIALFILLED = 2
    FILLED = 3
    CANCELED = 5
    PENDINGCANCEL = 6
    REJECTED = 8
    SUSPENDED = 9
    PENDINGNEW = 10
    EXPIRED = 12
