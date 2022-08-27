# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import csv
import datetime
import logging
import uuid
from os import path
from threading import Lock

from gmadaptor.common.utils import stockcode_to_myquant
from gmadaptor.gmclient.csvdata import GMExecReport, GMOrderReport
from gmadaptor.gmclient.heper_functions import (
    helper_set_gm_order_side,
    helper_set_gm_order_type,
)
from gmadaptor.gmclient.types import GMOrderBiz, GMOrderType
from gmadaptor.gmclient.wrapper import (
    get_gm_account_info,
    get_gm_in_csv_cancelorder,
    get_gm_in_csv_order,
    get_gm_out_csv_execreport,
    get_gm_out_csv_orderstatus,
)

logger = logging.getLogger(__name__)


# -----------------------  generate order or cancel order -------------------------
def csv_generate_orders(account_id: str, trade_info_list: list):
    # get account information
    acct_info = get_gm_account_info(account_id)
    if acct_info is None:
        return None

    in_file = get_gm_in_csv_order(acct_info)
    if in_file is None:
        return None

    # get lock object for this input file
    lock = acct_info[2]
    if lock is None:
        logger.error(
            "csv_generate_order: lock object for this account not found, %s", account_id
        )
        return None

    order_added = {}

    try:
        lock.acquire()

        add_head = False
        if not path.exists(in_file):
            add_head = True

        with open(in_file, "a+", encoding="utf-8-sig") as csvfile:
            if add_head:
                csvfile.write(
                    "sid,account_id,symbol,volume,order_type,order_business(order_biz),price,comment\n"
                )

            for trade_info in trade_info_list:
                security = trade_info["security"]
                volume = trade_info["volume"]
                price = trade_info["price"]
                order_side = trade_info["order_side"]
                order_type = trade_info["order_type"]
                sid = trade_info["cid"]

                _security = stockcode_to_myquant(security)
                _order_type = helper_set_gm_order_type(order_type)
                _order_side = helper_set_gm_order_side(order_side)

                csvfile.write(
                    f"{sid},{account_id},{_security},{volume},{_order_type},{_order_side},{price},\n"
                )
                order_added[sid] = trade_info
            # save to disk immediately
            csvfile.flush()
    except Exception as e:
        logger.warning("csv_generate_order: %s", e)
    finally:
        lock.release()

    return order_added


def csv_generate_cancel_orders(account_id: str, sid_list: list):
    # get account information
    acct_info = get_gm_account_info(account_id)
    if acct_info is None:
        return -1

    in_file = get_gm_in_csv_cancelorder(acct_info)
    if in_file is None:
        return -1

    # get lock object for this input file
    lock = acct_info[2]
    if lock is None:
        logger.error("lock object for this account not found: %s", account_id)
        return -1

    order_added = []

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
                order_added.append(sid)
            # save to disk immediately
            csvfile.flush()
    except Exception as e:
        logger.warning("csv_generate_order: %s", e)
    finally:
        lock.release()

    return order_added


# ------------------  generate order or cancel order ------ end ----------------


# 从执行回报中获取数据，如果sid_list非空，则过滤结果
def csv_get_exec_report_data(account_id: str, sid_list: list):
    exec_rpt_file = get_gm_out_csv_execreport(account_id)
    if not path.exists(exec_rpt_file):
        logger.error("execution report file not found: %s", exec_rpt_file)
        return None

    reports = {}
    with open(exec_rpt_file, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            report = GMExecReport(row)
            if report.exec_type != 15:  # 15成交，19执行有异常
                continue
            # 跳过异常数据后，只保留有效数据
            if not sid_list:
                if report.sid in reports:
                    reports[report.sid].append(report)
                else:
                    reports[report.sid] = [report]
                continue

            if report.sid in sid_list:
                if report.sid in reports:
                    reports[report.sid].append(report)
                else:
                    reports[report.sid] = [report]

    return reports


def csv_get_order_status_change_data_by_sidlist(status_file: str, sidlist: list):
    result_reports = {}
    with open(status_file, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            report = GMOrderReport(row)
            # 每次遍历所有数据，最后的总是最新的
            if report.sid in sidlist:
                result_reports[report.sid] = report

    # retry next time until timeout
    if len(result_reports) == 0:  # not found
        return {"result": -1}

    # 任何一个委托状态不确定时，返回结果等待下一次查询
    for sid in result_reports.keys():
        report = result_reports[sid]
        # 执行完毕状态: 3已成, 5, 已撤, 8已拒, 9挂起, 12已过期
        if report.status not in (3, 5, 8, 9, 12):
            # need retry: 2部成, 10待报, 1已报，6待撤
            return {"result": 1, "reports": result_reports}

    return {"result": 0, "reports": result_reports}


def csv_get_order_status(account_id: str):
    # 取出所有日内委托数据
    order_status_file = get_gm_out_csv_orderstatus(account_id)
    if not path.exists(order_status_file):
        logger.error("execution report file not found: %s", order_status_file)
        return None

    today = datetime.datetime.now()

    orders = []
    with open(order_status_file, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            order = GMOrderReport(row)
            ot = order.created_at
            if (
                ot.year == today.year
                and ot.month == today.month
                and ot.day == today.day
            ):
                logger.debug(
                    f"read order status of today: {order.sid} -> {order.cl_ord_id}, status: {order.status}"
                )
                orders.append(order)

    logger.debug("total orders read: %d", len(orders))
    return orders
