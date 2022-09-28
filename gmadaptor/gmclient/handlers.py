# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import csv
import logging

from gmadaptor.common.types import OrderSide, OrderStatus, OrderType
from gmadaptor.gmclient.csv_utils import (
    csv_generate_cancel_orders,
    csv_generate_orders,
    csv_get_exec_report_data,
    csv_get_order_status,
)
from gmadaptor.gmclient.csvdata import GMCash, GMPosition
from gmadaptor.gmclient.heper_functions import (
    helper_get_order_status_changes,
    helper_init_trade_event,
    helper_load_trade_event,
    helper_sum_exec_reports_by_sid,
)
from gmadaptor.gmclient.wrapper import get_gm_out_csv_cash, get_gm_out_csv_position

logger = logging.getLogger(__name__)


async def wrapper_get_balance(account_id: str):
    # 查询账户资金，返回cash结构
    out_dir = get_gm_out_csv_cash(account_id)
    if out_dir is None:
        return {"status": 401, "msg": "no output file found"}

    cash_in_csv = None
    # target csv file has BOM at the begining, using utf-8-sig instead of utf-8
    with open(out_dir, "r", encoding="utf-8-sig") as csvfile:
        for row in csv.DictReader(csvfile):
            cash_in_csv = row

    if not cash_in_csv:
        return {"status": 401, "msg": "no data in cash file"}

    acct_cash = {}
    try:
        _data = GMCash(cash_in_csv)
        acct_cash = _data.toDict()
    except Exception as e:
        logger.exception(e)
    return {"status": 200, "msg": "success", "data": acct_cash}


async def wrapper_get_positions(account_id: str):
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


def _build_trade_events_for_submitted(order_added: dict):
    tmp_events = {}
    for sid in order_added:
        trade_info = order_added[sid]
        tmp_event = helper_init_trade_event(trade_info)
        tmp_events[sid] = tmp_event.toDict()

    return tmp_events


def _build_trade_events_with_status_data(order_added: dict, status_reports: dict):
    result_events = {}
    for sid in order_added:
        trade_info = order_added[sid]
        if sid in status_reports:
            report = status_reports[sid]
            # 掘金模拟盘返回12超期，东财保持已报的状态，如果返回12已过期，强行改成已撤
            event = helper_load_trade_event(report)
        else:
            event = helper_init_trade_event(trade_info)
        result_events[sid] = event

    return result_events


def _build_trade_events_with_execrpts(event_list: dict, exec_reports: dict):
    result_events = {}
    for sid in event_list:
        event = event_list[sid]
        if event.status == OrderStatus.ERROR or event.status == OrderStatus.SUBMITTED:
            result_events[sid] = event.toDict()
            continue

        # 2,3,4的委托（以及过期的委托），再读取成交记录
        _rpts = exec_reports.get(sid, [])
        if _rpts:
            helper_sum_exec_reports_by_sid(_rpts, event)
            if event.invalid:  # 数据非法，并且已经清零
                logger.error(
                    "_build_events_rpts, invalid entrust: %s", event.entrust_no
                )
            else:
                if event.status == OrderStatus.ALL_TX and event.filled != event.volume:
                    event.status = OrderStatus.PARTIAL_TX
                result_events[sid] = event.toDict()
        else:
            # 无执行回报的情况下，只处理状态全成的委托，文件单一般不会出这样的错误，简单处理即可
            if event.status == OrderStatus.ALL_TX:  # 全成的委托回退一个状态，等待下次再取
                event.status = OrderStatus.PARTIAL_TX
            result_events[sid] = event.toDict()

    return result_events


async def wrapper_trade_action(
    account_id: str, trade_info_list: list, timeout: int = 1000
):
    # 写入扫单文件
    order_added = await csv_generate_orders(account_id, trade_info_list)
    if not order_added:  # 一个都没写入，全部撤回
        return {"status": 501, "msg": "failed to append data to order file"}

    # 读取状态变化文件，传递超时参数
    sidlist = order_added.keys()
    status_reports = await helper_get_order_status_changes(account_id, sidlist, timeout)
    if not status_reports:  # 文件单输出模式启动失败（文件不存在），或者服务异常
        # 已经写入文件单的委托返回“已报”
        _data = _build_trade_events_for_submitted(order_added)
        return {"status": 200, "msg": "return with errors", "data": _data}

    # 构建返回的委托结果字典
    event_list = _build_trade_events_with_status_data(order_added, status_reports)

    # 取出所有执行报告中的委托数据
    new_sid_list = list(status_reports.keys())
    exec_reports = await csv_get_exec_report_data(account_id, new_sid_list)
    if exec_reports is None:
        logger.error("not data found in exec report file: %s", new_sid_list)
        exec_reports = {}

    result_events = _build_trade_events_with_execrpts(event_list, exec_reports)
    return {"status": 200, "msg": "success", "data": result_events}


async def wrapper_cancel_entursts(account_id: str, sid_list: list):
    # 如果撤销操作失败，调用者得不到任何反馈，可以继续撤销，因此不用特殊处理各种异常情况
    if sid_list is None or (not isinstance(sid_list, list)):
        return {"status": 401, "msg": "only entrust list accepted"}
    if not sid_list:
        return {"status": 401, "msg": "empty entrust list detected"}

    sid_added = await csv_generate_cancel_orders(account_id, sid_list)
    if not sid_added:
        return {
            "status": 401,
            "msg": "failed to append data to order cancel file",
        }

    # 从状态更新文件中读取撤销结果，字典数据
    status_reports = await helper_get_order_status_changes(account_id, sid_added, 1000)
    if not status_reports:
        return {
            "status": 500,
            "msg": f"cancel_entrusts, status change not found: {account_id}",
        }

    # 读取有效委托的执行回报数据
    new_sid_list = list(status_reports.keys())
    exec_reports = await csv_get_exec_report_data(account_id, new_sid_list)
    if exec_reports is None:  # 无数据不影响撤销的正确性，以委托的最终状态为准
        return {"status": 500, "msg": "cancel_entrusts, exec report file not found"}

    event_list = {}
    # order_status无成交信息，order_status_change无成交价格
    for report in status_reports.values():
        event = helper_load_trade_event(report)
        event_list[event.entrust_no] = event

    result_events = _build_trade_events_with_execrpts(event_list, exec_reports)
    return {"status": 200, "msg": "success", "data": result_events}


async def wrapper_get_today_all_entrusts(account_id: str):
    # 取出所有日内委托数据
    all_entrusts = await csv_get_order_status(account_id)
    if not all_entrusts:
        return {
            "status": 500,
            "msg": "today_entrusts, order status not found of this account",
        }

    # 取出所有执行报告中的委托数据
    all_exec_rpts = await csv_get_exec_report_data(account_id, None)
    if all_exec_rpts is None:
        return {"status": 500, "msg": "today_entrusts, exec report file not found"}

    event_list = {}
    for entrust in all_entrusts:
        event = helper_load_trade_event(entrust)
        event_list[event.entrust_no] = event

    result_events = _build_trade_events_with_execrpts(event_list, all_exec_rpts)
    return {"status": 200, "msg": "success", "data": result_events}


# 以下接口暂为自用目的，Z trade server不对接


async def wrapper_get_today_trades(account_id: str):
    # 取出所有的执行报告，均为交易成功的委托，买或者卖
    reports = await csv_get_exec_report_data(account_id, None)
    if reports is None:
        return {"status": 500, "msg": "execution report file not found of this account"}

    datalist = []
    for report in reports:
        datalist.append(report.toDict())
    return {"status": 200, "msg": "success", "data": datalist}
