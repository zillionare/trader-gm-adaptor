# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import csv
import logging
from time import sleep

from cfg4py.config import Config
from gmadaptor.common.name_conversion import stockcode_to_myquant
from gmadaptor.common.types import OrderSide, OrderStatus, OrderType
from gmadaptor.gmclient.csv_utils import (
    csv_generate_cancel_order,
    csv_generate_order,
    csv_get_exec_report_data,
    csv_get_order_status,
    csv_get_unfinished_entrusts_from_order_status,
)
from gmadaptor.gmclient.csvdata import GMCash, GMPosition
from gmadaptor.gmclient.heper_functions import (
    helper_get_data_from_exec_reports,
    helper_get_order_status_change_by_sidlist,
    helper_get_order_status_change_data,
    helper_load_trade_event,
    helper_set_gm_order_side,
    helper_set_gm_order_type,
    helper_sum_exec_reports_by_sid,
)
from gmadaptor.gmclient.wrapper import get_gm_out_csv_cash, get_gm_out_csv_position

logger = logging.getLogger(__name__)


def wrapper_get_balance(account_id: str):
    # 查询账户资金，返回cash结构
    out_dir = get_gm_out_csv_cash(account_id)
    if out_dir is None:
        return {"status": 401, "msg": "no output file found"}

    cash_in_csv = None
    # target csv file has BOM at the begining, using utf-8-sig instead of utf-8
    with open(out_dir, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            cash_in_csv = row

    if cash_in_csv is None:
        return {"status": 401, "msg": "no data in cash file"}

    acct_cash = GMCash(cash_in_csv)
    return {"status": 200, "msg": "success", "data": acct_cash.toDict()}


def wrapper_get_positions(account_id: str):
    # 获取登录账户的持仓，如登录多个账户需要指定账户ID
    out_dir = get_gm_out_csv_position(account_id)
    if out_dir is None:
        return {"status": 401, "msg": "no output file found"}

    poses = []
    # target csv file has BOM at the begining, using utf-8-sig instead of utf-8
    with open(out_dir, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            pos = GMPosition(row)
            poses.append(pos.toDict())

    return {"status": 200, "msg": "success", "data": poses}


def wrapper_trade_operation(
    account_id: str,
    security: str,
    volume: int,
    price: float,
    order_side: OrderSide,
    order_type: OrderType,
    limit_price: float = None,
    timeout_in_action: float = 1000,  # 毫秒
):
    myquant_code = stockcode_to_myquant(security)
    gm_order_side = helper_set_gm_order_side(order_side)
    gm_order_type = helper_set_gm_order_type(order_type)

    sid = csv_generate_order(
        account_id, myquant_code, volume, gm_order_side, gm_order_type, price
    )
    # sid = "69724e8e-a680-11ec-a4d3-a5d7002ce96d"
    if sid is None:
        return {"status": 401, "msg": "failed to append data to input file"}

    params = {"timeout": timeout_in_action}
    # 读取状态变化文件，所有的委托状态均可查询，比如价格错误，股票错误等等
    reports = helper_get_order_status_change_data(account_id, sid, params)
    if reports is None:
        return {"status": 500, "msg": "委托状态变化文件没找到"}
    if len(reports) == 0:
        return {"status": 500, "msg": "failed to get result of this entrust"}

    report = reports[0]
    timeout_in_action = params["timeout"]  # 下个操作的超时时间

    # 读取状态变化文件中的委托信息
    event = helper_load_trade_event(report)

    # 状态不是（已成3，部成2）情况的委托，直接返回结果
    status = report.status
    if status != 2 and status != 3:
        return {"status": 200, "msg": "success", "data": event.toDict()}

    # 2和3的委托，再读取成交记录
    exec_reports = helper_get_data_from_exec_reports(
        account_id, sid, event, timeout_in_action
    )
    if exec_reports is None:
        return {"status": 500, "msg": "执行回报文件没找到"}
    if len(exec_reports) == 0:
        # 查询不到结果，留给z trade server后续校正
        return {"status": 500, "msg": "failed to get result of this entrust"}

    return {"status": 200, "msg": "success", "data": event.toDict()}


def wrapper_cancel_entursts(account_id: str, sid_list):
    # 构建撤销委托的数组
    if sid_list is None or (not isinstance(sid_list, list)):
        return {"status": 401, "msg": "only entrust list accepted"}

    result = csv_generate_cancel_order(account_id, sid_list)
    if result != 0:
        return {
            "status": 401,
            "msg": "failed to append data to input file, check lock or file",
        }

    # 从状态更新文件中读取撤销结果，{}字典
    reports = helper_get_order_status_change_by_sidlist(account_id, sid_list)
    if reports is None:
        return {"status": 500, "msg": f"委托状态变化文件没找到: {account_id}"}
    if len(reports) == 0:
        return {"status": 500, "msg": "failed to get result of these entrusts"}

    # 重新生成SID列表，可能有的委托从状态变化文件中读取失败了
    new_sid_list = list(reports.keys())

    # 取出所有执行报告中的委托数据
    all_exec_reports = csv_get_exec_report_data(account_id, new_sid_list)
    if all_exec_reports is None:
        return {"status": 500, "msg": "执行回报文件没找到"}

    result_events = {}
    # 撤销委托的order_status数据里面，没有成交信息，order_status_change里面没有成交价格
    for report in reports.values():
        event = helper_load_trade_event(report)
        # 装载执行回报中的数据
        if len(all_exec_reports) > 0:
            helper_sum_exec_reports_by_sid(all_exec_reports, event)

        result_events[event.entrust_no] = event.toDict()

    return {"status": 200, "msg": "OK", "data": result_events}


def wrapper_get_today_all_entrusts(account_id: str):
    # 取出所有日内委托数据
    all_entrusts = csv_get_order_status(account_id)
    if all_entrusts is None:
        return {"status": 500, "msg": "order status file not found of this account"}

    # 取出所有执行报告中的委托数据
    all_exec_reports = csv_get_exec_report_data(account_id, None)
    if all_exec_reports is None:
        return {"status": 500, "msg": "执行回报文件没找到"}

    result_events = {}
    for entrust in all_entrusts:
        event = helper_load_trade_event(entrust)
        event_status = event.status
        if event_status == OrderStatus.ERROR or event_status == OrderStatus.NO_DEAL:
            # 无成交数据返回的情况
            result_events[event.entrust_no] = event.toDict()
            continue

        # 装载执行回报中的数据
        if len(all_exec_reports) > 0:
            helper_sum_exec_reports_by_sid(all_exec_reports, event)

        result_events[event.entrust_no] = event.toDict()

    return {"status": 200, "msg": "success", "data": result_events}


# 以下3个接口暂为自用目的，Z trade server不对接


def wrapper_get_unfinished_entursts(account_id: str):
    # 条件分别为：SID有效，时间在今天，委托未完成（不包括已成，已撤，已过期）
    entrusts = csv_get_unfinished_entrusts_from_order_status(account_id)
    if entrusts is None:
        return {"status": 500, "msg": "order status file not found of this account"}

    datalist = []
    for entrust in entrusts:
        datalist.append(entrust.toDict())
    return {"status": 200, "msg": "success", "data": datalist}


def wrapper_get_today_trades(account_id: str):
    # 取出所有的执行报告，均为交易成功的委托，买或者卖
    reports = csv_get_exec_report_data(account_id, None)
    if reports is None:
        return {"status": 500, "msg": "execution report file not found of this account"}

    datalist = []
    for report in reports:
        datalist.append(report.toDict())
    return {"status": 200, "msg": "success", "data": datalist}
