# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import asyncio
import csv
import logging
from time import sleep

import cfg4py
from cfg4py.config import Config
from gmadaptor.common.name_conversion import (
    stockcode_to_joinquant,
    stockcode_to_myquant,
)
from gmadaptor.common.types import BidType, OrderSide
from gmadaptor.gmclient.csv_utils import (
    csv_generate_cancel_order,
    csv_generate_order,
    csv_get_exec_report_data,
    csv_get_order_status,
    csv_get_order_status_change_data,
    csv_get_unfinished_entrusts_from_order_status,
)
from gmadaptor.gmclient.csvdata import gm_cash, gm_position
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


def wrapper_buy(account_id: str, security: str, price: float, volume: int):
    myquant_code = stockcode_to_myquant(security)

    if price is None:
        logger.info("price not provided in order entrust: %s, %s", account_id, security)
        return {"status": 401, "msg": "price cannot be None"}

    sid = csv_generate_order(
        account_id, myquant_code, volume, OrderSide.BUY, BidType.LIMIT, price
    )
    if sid is None:
        return {"status": 401, "msg": "failed to append data to input file"}

    sleep(0.2)
    status_file = get_gm_out_csv_order_status_change(account_id)
    print(f"exec report file: {status_file}")
    result = csv_get_order_status_change_data(status_file, sid)
    if result is None:
        return {"status": 500, "msg": "failed to open report file"}

    return {"status": 200, "msg": "success", "data": result}


def wrapper_market_buy(
    account_id: str, security: str, volume: int, limit_price: float = None
):
    myquant_code = stockcode_to_myquant(security)

    # 市价成交暂定价格为0，根据实际客户端调整
    price = 0
    sid = csv_generate_order(
        account_id, myquant_code, volume, OrderSide.BUY, BidType.MARKET, price
    )
    if sid is None:
        return {
            "status": 401,
            "msg": "failed to append data to input file, check lock or file",
        }

    sleep(0.2)
    status_file = get_gm_out_csv_order_status_change(account_id)
    print(f"exec report file: {status_file}")
    result = csv_get_order_status_change_data(status_file, sid)
    if result is None:
        return {"status": 500, "msg": "failed to open report file"}

    return {"status": 200, "msg": "success", "data": result}


def wrapper_sell(account_id: str, security: str, price: float, volume: int):
    myquant_code = stockcode_to_myquant(security)

    if price is None:
        return {"status": 401, "msg": "price cannot be None [sell]"}

    sid = csv_generate_order(
        account_id, myquant_code, volume, OrderSide.SELL, BidType.LIMIT, price
    )
    if sid is None:
        return {
            "status": 401,
            "msg": "failed to append data to input file, check lock or file",
        }

    sleep(0.2)
    status_file = get_gm_out_csv_order_status_change(account_id)
    print(f"exec report file: {status_file}")
    result = csv_get_order_status_change_data(status_file, sid)
    if result is None:
        return {"status": 500, "msg": "failed to open report file"}

    return {"status": 200, "msg": "success", "data": result}


def wrapper_market_sell(
    account_id: str, security: str, volume: int, limit_price: float = None
):
    myquant_code = stockcode_to_myquant(security)

    # 市价成交暂定价格为0，根据实际客户端调整
    price = 0
    sid = csv_generate_order(
        account_id, myquant_code, volume, OrderSide.SELL, BidType.MARKET, price
    )
    if sid is None:
        return {
            "status": 401,
            "msg": "failed to append data to input file, check lock or file",
        }

    sleep(0.2)
    status_file = get_gm_out_csv_order_status_change(account_id)
    print(f"exec report file: {status_file}")
    result = csv_get_order_status_change_data(status_file, sid)
    if result is None:
        return {"status": 500, "msg": "failed to open report file"}

    return {"status": 200, "msg": "success", "data": result}


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
    print(f"exec report file: {status_file}")
    last_stataus = csv_get_order_status_change_data(status_file, sid)

    return {"status": 200, "msg": "success", "data": {"status": last_stataus}}


def wrapper_cancel_all_enturst(account_id: str):
    # 行为待定，取消所有委托，如果是当天所有未完成的委托，则需要逐个查找order_status.csv里面，所有未完成的委托
    # 找到所有的sid之后，再写入cancel_order.csv文件中
    # 条件分别为：SID有效，时间在今天，委托未完成（不包括已成，已撤，已过期）
    order_status_file = get_gm_out_csv_orderstatus(account_id)
    print(f"order status file: {order_status_file}")

    entrusts = csv_get_unfinished_entrusts_from_order_status(order_status_file)
    if entrusts is not None and len(entrusts) > 0:
        result = csv_generate_cancel_order(account_id, "", entrusts)
        if result is None:
            return {
                "status": 401,
                "msg": "failed to append data to input file, check lock or file",
            }

    return {"status": 200, "msg": "success"}


def wrapper_get_today_entrusts(account_id: str):
    order_status_file = get_gm_out_csv_orderstatus(account_id)
    print(f"order status file: {order_status_file}")

    entrusts = csv_get_order_status(order_status_file)
    return {"status": 200, "msg": "success", "data": entrusts}


def wrapper_get_today_trades(account_id: str):
    orders_file = get_gm_out_csv_execreport(account_id)
    print(f"execution report file: {orders_file}")

    orders = csv_get_exec_report_data(orders_file)
    return {"status": 200, "msg": "success", "data": orders}
