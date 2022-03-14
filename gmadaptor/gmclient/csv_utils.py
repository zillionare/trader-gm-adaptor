# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import csv
import datetime
import logging
import os
import uuid
from os import path
from threading import Lock

from gmadaptor.common.types import BidType, OrderSide
from gmadaptor.gmclient.data_conversion import (
    gm_exec_report,
    gm_order_status,
    gm_order_status_change,
)
from gmadaptor.gmclient.types import OrderBiz, OrderType
from gmadaptor.gmclient.wrapper import (
    get_gm_account_info,
    get_gm_in_csv_cancelorder,
    get_gm_in_csv_order,
    get_gm_out_csv_cash,
    get_gm_out_csv_execreport,
    get_gm_out_csv_position,
)

logger = logging.getLogger(__name__)

"""
order_type 委托类型
深圳市场
    1    限价
    20    市价, 对方最优价格 (best of counterparty)
    21    市价, 己方最优价格 (best of party)
    22    市价, 即时成交剩余撤销 (fill and kill)
    23    市价, 即时全额成交或撤销 (fill or kill)
    24    市价, 最优五档剩余撤销 (best 5 then cancel)
上海市场
    1    限价
    24    市价, 最优五档剩余撤销 (best 5 then cancel)
    25    市价, 最优五档剩余转限价(best 5 then limit)

order_biz 委托业务类型
股票
    1    股票, 买入
    2    股票, 卖出
期货
    10    期货, 买入开仓
    11    期货, 卖出平仓
    12    期货, 卖出平仓, 平今仓 (上海商品期货交易所 only)
    13    期货, 卖出平仓, 平昨仓 (上海商品期货交易所 only)
    14    期货, 卖出开仓
    15    期货, 买入平仓
    16    期货, 买入平仓，平今仓 (上海商品期货交易所 only)
    17    期货, 买入平仓, 平昨仓 (上海商品期货交易所 only)
"""


"""
sid    string    是    用户策略定义的交易指令ID, 唯一性, 不可重复使用
account_id    string    是    掘金交易账号ID
symbol    string    是    标的代码, 格式: 市场.代码 例如:平安银行 SZSE.000001 浦发银行 SHSE.600000
volume    number    是    委托量, 整数
order_type    string    是    委托类型, 请参考下面的数据字典定义 参见
order_business(order_biz)    string    是    委托业务类型, 请参考下面的数据字典定义 注：参数名必须带括号里面的字段 参见
price    number    否    委托价格. 当委托类型为限价单时, 必填
comment    string    否    备注说明, 不需要时可给空字符串.
"""


def csv_generate_order(
    account_id: str,
    symbol: str,
    volume: int,
    order_side: OrderSide,
    order_type: BidType,
    price: float = None,
):
    # get account information
    acct_info = get_gm_account_info(account_id)
    if acct_info is None:
        return None

    in_file = get_gm_in_csv_order(account_id)
    if in_file is None:
        return None

    # get lock object for this input file
    lock = acct_info[2]
    if lock is None:
        logger.error("lock object for this account not found: %s", account_id)
        return None

    try:
        lock.acquire()

        # get UUID and convert to string
        sid = str(uuid.uuid1())

        add_head = False
        if not path.exists(in_file):
            add_head = True

        with open(in_file, "a+", encoding="utf-8-sig") as csvfile:
            if add_head:
                csvfile.write(
                    "sid,account_id,symbol,volume,order_type,order_business(order_biz),price,comment\n"
                )

            order_biz = OrderBiz.BUY
            if order_side == OrderSide.SELL:
                order_biz = OrderBiz.SELL

            gm_order_type = OrderType.LIMITPRICE
            if order_type == BidType.MARKET:
                gm_order_type = OrderType.BESTCANCEL

            csvfile.write(
                f"{sid},{account_id},{symbol},{volume},{gm_order_type},{order_biz},{price},\n"
            )

            # save to disk immediately
            csvfile.flush()

        return sid

    finally:
        lock.release()


def csv_generate_cancel_order(account_id: str, symbol: str, sid: str):
    # get account information
    acct_info = get_gm_account_info(account_id)
    if acct_info is None:
        return None

    in_file = get_gm_in_csv_cancelorder(account_id)
    if in_file is None:
        return None

    # get lock object for this input file
    lock = acct_info[2]
    if lock is None:
        logger.error("lock object for this account not found: %s", account_id)
        return None

    try:
        lock.acquire()

        add_head = False
        if not path.exists(in_file):
            add_head = True

        with open(in_file, "a+", encoding="utf-8-sig") as csvfile:
            if add_head:
                csvfile.write("sid,comment\n")

            csvfile.write(f"{sid},comments,\n")

            # save to disk immediately
            csvfile.flush()

        return sid

    finally:
        lock.release()


def csv_get_exec_report_data(rpt_file: str, sid: str):
    if not path.exists(rpt_file):
        logger.error("execution report file not found: %s", rpt_file)
        return None

    with open(rpt_file, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            report = gm_exec_report(row)
            if report.sid == sid:
                return report.cl_ord_id

    logger.info("sid not found in exec report file: %s", sid)
    return None


def csv_get_exec_report_data2(rpt_file: str):
    if not path.exists(rpt_file):
        logger.error("execution report file not found: %s", rpt_file)
        return None

    reports = []
    with open(rpt_file, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            report = gm_exec_report(row)
            print(f"read exec report line: {report.sid}")
            reports.append(report.toDict())

    print("report cound: ", len(reports))
    return reports


def csv_get_order_status_change_data(status_file: str, sid: str):
    if not path.exists(status_file):
        logger.error("execution report file not found: %s", status_file)
        return None

    order_status = 0
    with open(status_file, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            report = gm_order_status_change(row)
            print(f"read order status change dataline: {report.sid}")
            # 应该获取时间最新的数据，返回给用户，暂时简化处理
            if sid == report.sid:
                if order_status == 0 or order_status == 1:
                    print(f"order status read: {sid} -> {report.status}")
                    order_status = report.status

    return order_status


# order_status.csv
def csv_get_order_status(orders_file: str):
    if not path.exists(orders_file):
        logger.error("execution report file not found: %s", orders_file)
        return None

    today = datetime.datetime.now()

    orders = []
    with open(orders_file, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            order = gm_order_status(row)
            ot = order.created_at
            if (
                ot.year == today.year
                and ot.month == today.month
                and ot.day == today.day
            ):
                print(f"read order status of today: {order.cl_ord_id}")
                orders.append(order.toDict())

    print("order cound: ", len(orders))
    return orders
