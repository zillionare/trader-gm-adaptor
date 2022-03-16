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
from gmadaptor.gmclient.csvdata import (
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


def csv_generate_cancel_order(account_id: str, symbol: str, sid_list: list):
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

            for sid in sid_list:
                csvfile.write(f"{sid},comments,\n")

            # save to disk immediately
            csvfile.flush()

        return 0

    finally:
        lock.release()


def csv_get_exec_report_data(rpt_file: str):
    if not path.exists(rpt_file):
        logger.error("execution report file not found: %s", rpt_file)
        return None

    reports = []
    with open(rpt_file, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            report = gm_exec_report(row)
            logger.debug(f"read exec report line: {report.sid}")
            reports.append(report.toDict())

    logger.debug("total report read: ", len(reports))
    return reports


def csv_get_exec_report_data_by_sid(rpt_file: str, sid: str):
    if not path.exists(rpt_file):
        logger.error("execution report file not found: %s", rpt_file)
        return None

    # ExecType_Trade = 15 # 成交(有效)
    reports = []
    exec_type = 0

    with open(rpt_file, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            report = gm_exec_report(row)
            logger.debug(f"read exec report line: {report.sid}")
            if sid == report.sid:
                reports.append(report)
                exec_type = report.exec_type

    # retry next time until timeout
    if len(reports) == 0:
        return {"result": 0}

    exec_type = report.exec_type
    if exec_type == 15:
        return {"result": 2, "reports": reports}
    else:
        # need retry
        return {"result": 1, "reports": reports}


def csv_get_order_status_change_data(status_file: str, sid: str):
    if not path.exists(status_file):
        logger.error("order status change file not found: %s", status_file)
        return None

    result_report = None

    # 10待报, 1已报，6待撤
    # 2部成, 3已成, 5, 已撤, 8已拒, 9挂起, 12已过期
    with open(status_file, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            report = gm_order_status_change(row)
            # print(f"read order status change dataline: {report.sid}")
            # 应该获取时间最新的数据，返回给用户，暂时简化处理
            if sid == report.sid:
                result_report = report

    # retry next time until timeout
    if result_report is None:
        return {"result": 0}

    status = report.status
    # 执行完毕状态
    if status == 3 or status == 5 or status == 8 or status == 9 or status == 12:
        return {"result": 2, "report": result_report}
    else:
        # need retry
        return {"result": 1, "report": result_report}


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
                logger.debug(
                    f"read order status of today: {order.sid} -> {order.cl_ord_id}"
                )
                orders.append(order.toDict())

    logger.debug("total orders read: ", len(orders))
    return orders


def csv_get_unfinished_entrusts_from_order_status(orders_file: str):
    """
    OrderStatus_Filled = 3                # 已成
    OrderStatus_Canceled = 5              # 已撤
    OrderStatus_Rejected = 8              # 已拒绝
    OrderStatus_Expired = 12              # 已过期

    """
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
                if (
                    order.status != 3
                    and order.status != 5
                    and order.status != 8
                    and order.status != 12
                ):
                    logger.debug(
                        "entrust to be canceled: %s  -> %d", order.sid, order.status
                    )
                    orders.append(order)

    logger.debug("entrust to be canceled: %d", len(orders))
    return orders
