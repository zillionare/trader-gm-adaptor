# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import asyncio
import csv
import logging
from ast import While
from time import sleep

import cfg4py
from cfg4py.config import Config
from gmadaptor.common.name_conversion import (
    stockcode_to_joinquant,
    stockcode_to_myquant,
)
from gmadaptor.common.types import BidType, OrderSide, TradeEvent, TradeOrder
from gmadaptor.gmclient.csv_utils import (
    csv_generate_cancel_order,
    csv_generate_order,
    csv_get_exec_report_data,
    csv_get_exec_report_data_by_sid,
    csv_get_order_status,
    csv_get_order_status_change_data,
    csv_get_unfinished_entrusts_from_order_status,
)
from gmadaptor.gmclient.csvdata import gm_cash, gm_order_status, gm_position
from gmadaptor.gmclient.wrapper import (
    get_gm_account_info,
    get_gm_in_csv_cancelorder,
    get_gm_in_csv_order,
    get_gm_out_csv_cash,
    get_gm_out_csv_execreport,
    get_gm_out_csv_order_status_change,
    get_gm_out_csv_orderstatus,
    get_gm_out_csv_position,
)

logger = logging.getLogger(__name__)


def wrapper_get_balance(account_id: str):
    # 查询账户资金，返回cash结构
    out_dir = get_gm_out_csv_cash(account_id)
    if out_dir is None:
        return {"status": 401, "msg": "no output file found"}

    mycash = None
    # target csv file has BOM at the begining, using utf-8-sig instead of utf-8
    with open(out_dir, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            mycash = row

    if mycash is None:
        return {"status": 401, "msg": "no data in cash file"}

    return {"status": 200, "msg": "success", "data": gm_cash(mycash).toDict()}


def wrapper_get_positions(account_id: str):
    # 获取登录账户的持仓，如登录多个账户需要指定账户ID
    out_dir = get_gm_out_csv_position(account_id)
    if out_dir is None:
        return {"status": 401, "msg": "no output file found"}

    poses = []
    # target csv file has BOM at the begining, using utf-8-sig instead of utf-8
    with open(out_dir, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            pos = gm_position(row)
            poses.append(pos.toDict())

    if len(poses) == 0:
        return {"status": 401, "msg": "no data in position file"}

    return {"status": 200, "msg": "success", "data": poses}


def wrapper_trade_operation(
    account_id: str,
    security: str,
    volume: int,
    price: float,
    order_side: OrderSide,
    bid_type: BidType,
    limit_price: float = None,
):
    myquant_code = stockcode_to_myquant(security)

    sid = csv_generate_order(
        account_id, myquant_code, volume, order_side, bid_type, price
    )
    if sid is None:
        return {"status": 401, "msg": "failed to append data to input file"}

    report = None

    # 读取状态变化文件，所有的委托状态均可查询，比如价格错误，股票错误等等
    status_file = get_gm_out_csv_order_status_change(account_id)
    # print(f"exec report change file: {status_file}")

    timeout = 5000  # 默认5000毫秒
    while timeout > 0:
        result = csv_get_order_status_change_data(status_file, sid)
        if result is None:
            return {
                "status": 500,
                "msg": "order status change file not found of this account",
            }

        result_status = result["result"]
        if result_status != 0:
            report = result["report"]
        if result_status == 2:
            break

        sleep(100 / 1000)
        timeout -= 100

    if report is None:
        return {"status": 500, "msg": "failed to get result of this entrust"}

    # 状态成功之后，再读取具体的成交记录，特指已成3，部成2等情况
    status = report.status
    if status != 2 and status != 3:
        event = TradeEvent(
            report.symbol,
            0,
            volume,
            order_side,
            bid_type,
            report.created_at,
            report.sid,
            report.status,
            0.0,
            0,
            report.order_id,
            0,
            report.rej_detail,
            report.recv_at,
        )
        return {"status": 200, "msg": "success", "data": event.toDict()}

    exec_reports = None
    status_file = get_gm_out_csv_execreport(account_id)
    # print(f"exec report file: {status_file}")

    timeout = 1000  # 默认1000毫秒
    while timeout > 0:
        result = csv_get_exec_report_data_by_sid(status_file, sid)
        if result is None:
            return {"status": 500, "msg": "exec report file not found of this account"}

        status = result["result"]
        if status != 0:
            exec_reports = result["reports"]
        if status == 2:
            break

        sleep(100 / 1000)
        timeout -= 100

    if exec_reports is None:
        return {"status": 500, "msg": "failed to get result of this entrust"}

    # 最后完成交易的时间
    recv_at = None
    total_volume = 0
    total_amount = 0.0  # 总资金量
    for exec_report in exec_reports:
        total_volume += exec_report.volume
        total_amount += exec_report.volume * exec_report.price
        recv_at = exec_report.recv_at

    event = TradeEvent(
        security,
        0,
        volume,
        order_side,
        bid_type,
        report.created_at,
        report.sid,
        report.status,
        total_amount / total_volume,
        total_volume,
        report.order_id,
        0,
        "",
        recv_at,
    )
    return {"status": 200, "msg": "success", "data": event.toDict()}


def wrapper_cancel_enturst(account_id: str, security: str, sid: str):
    myquant_code = stockcode_to_myquant(security)

    sid_list = [sid]
    sid = csv_generate_cancel_order(account_id, myquant_code, sid_list)
    if sid is None:
        return {
            "status": 401,
            "msg": "failed to append data to input file, check lock or file",
        }

    sleep(0.2)
    status_file = get_gm_out_csv_order_status_change(account_id)
    logger.debug(f"cancel_enturst, exec report file: {status_file}")
    last_stataus = csv_get_order_status_change_data(status_file, sid)

    return {"status": 200, "msg": "success", "data": {"status": last_stataus}}


def wrapper_get_unfinished_entursts(account_id: str):
    # 条件分别为：SID有效，时间在今天，委托未完成（不包括已成，已撤，已过期）
    order_status_file = get_gm_out_csv_orderstatus(account_id)
    logger.debug(f"get_unfinished_entursts, order status file: {order_status_file}")

    entrusts = csv_get_unfinished_entrusts_from_order_status(order_status_file)
    if entrusts is None:
        return {"status": 500, "msg": "order status file not found of this account"}

    events = []
    for entrust in entrusts:
        event = TradeEvent(
            entrust.symbol,
            entrust.price,
            entrust.volume,
            entrust.order_business,
            entrust.order_type,
            entrust.created_at,
            entrust.sid,
            entrust.status,
            0,
            0,
            entrust.order_id,
            0,
            "",
            entrust.recv_at,
        )
        events.append(event.toDict())
    return {"status": 200, "msg": "success", "data": events}


# 以下3个接口暂为自用目的，Z trader server不对接


def wrapper_get_today_all_entrusts(account_id: str):
    order_status_file = get_gm_out_csv_orderstatus(account_id)
    logger.debug(f"get_today_all_entrusts, order status file: {order_status_file}")

    entrusts = csv_get_order_status(order_status_file)
    return {"status": 200, "msg": "success", "data": entrusts}


def wrapper_get_today_entrusts(account_id: str):
    order_status_file = get_gm_out_csv_orderstatus(account_id)
    logger.debug(f"get_today_entrusts, order status file: {order_status_file}")

    entrusts = csv_get_unfinished_entrusts_from_order_status(order_status_file)
    return {"status": 200, "msg": "success", "data": entrusts}


def wrapper_get_today_trades(account_id: str):
    orders_file = get_gm_out_csv_execreport(account_id)
    logger.debug(f"get_today_trades, execution report file: {orders_file}")

    orders = csv_get_exec_report_data(orders_file)
    return {"status": 200, "msg": "success", "data": orders}
