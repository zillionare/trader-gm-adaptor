from asyncio.log import logger
from time import sleep

import cfg4py
from gmadaptor.common.name_conversion import (
    get_stock_location,
    stockcode_to_joinquant,
    stockcode_to_myquant,
)
from gmadaptor.common.types import (
    OrderSide,
    OrderStatus,
    OrderType,
    TradeEvent,
    TradeOrder,
)
from gmadaptor.gmclient.csv_utils import (
    csv_get_exec_report_data_by_sid,
    csv_get_order_status_change_data_by_sid,
    csv_get_order_status_change_data_by_sidlist,
)
from gmadaptor.gmclient.csvdata import GMCash, GMExecReport, GMOrderReport, GMPosition
from gmadaptor.gmclient.types import GMOrderBiz, GMOrderType


def helper_load_trade_event(order_status_record: GMOrderReport) -> TradeEvent:
    event = TradeEvent(
        stockcode_to_joinquant(order_status_record.symbol),
        order_status_record.price,
        order_status_record.volume,
        OrderSide.convert(order_status_record.order_side),
        OrderType.convert(order_status_record.order_type),
        order_status_record.created_at,
        order_status_record.sid,
        OrderStatus.convert(order_status_record.status),
        0.0,
        0,
        order_status_record.order_id,
        0,
        order_status_record.rej_detail,
        order_status_record.recv_at,
    )

    return event


def helper_calculate_trade_fees(amount, fees_info, order_side):
    """交易费用计算
    commission: 0.03  # 券商佣金，万分之三
    stamp_duty: 0.1 # 印花税，千分之一
    transfer_fee: 0.002 # 过户费，万分之0.2
    minimum_cost: 5.0 # 最低佣金
    """
    commission = amount * fees_info.commission / 10000
    if commission < fees_info.minimum_cost:
        commission = fees_info.minimum_cost
    transfer_fee = amount * fees_info.transfer_fee / 10000

    stamp_duty = 0
    if order_side == 2:
        stamp_duty = amount * fees_info.stamp_duty / 10000

    return commission + transfer_fee + stamp_duty


def helper_get_exec_reports_by_sid(exec_reports, event):
    server_config = cfg4py.get_instance()
    trade_fees = server_config.gm_info.trade_fees

    total_volume = 0
    total_amount = 0.0  # 总资金量
    total_commission = 0  # 总手续费
    recv_at = None  # 最后完成交易的时间

    my_exec_rpts = []
    for exec_rpt in exec_reports:  # 从执行回报中取详细数据
        if exec_rpt.sid == event.entrust_no:
            my_exec_rpts.append(exec_rpt)

            total_volume += exec_rpt.volume
            total_amount += exec_rpt.volume * exec_rpt.price
            total_commission += helper_calculate_trade_fees(
                total_amount, trade_fees, exec_rpt.order_side
            )
            recv_at = exec_rpt.recv_at

    # 平均价格的计算暂时不纳入手续费
    if total_volume == 0:
        event.avg_price = 0
    else:
        event.avg_price = total_amount / total_volume
    event.filled = total_volume
    event.trade_fees = total_commission
    if recv_at is not None:
        event.recv_at = recv_at


def helper_reset_event(event):
    event.avg_price = 0
    event.filled = 0
    event.trade_fees = 0
    event.recv_at = event.create_at


def helper_set_gm_order_side(order_side):
    if order_side == OrderSide.SELL:
        return GMOrderBiz.SELL

    else:
        return GMOrderBiz.BUY


def helper_set_gm_order_type(order_type):
    # 市价成交，无须价格，除非是限价委托（即时成交，剩余转限价）
    if order_type == OrderType.MARKET:
        return GMOrderType.BESTCANCEL
    return GMOrderType.LIMITPRICE


def helper_get_order_from_status_change_file(account_id, sid, params):
    timeout_in_action = params["timeout"]

    report = None
    while timeout_in_action > 0:
        result = csv_get_order_status_change_data_by_sid(account_id, sid)
        if result is None:
            logger.warning(
                "order status change file not found of this account: %s", account_id
            )
            return None

        result_status = result["result"]
        if result_status != -1:  # 保存查询到的结果，继续查看
            report = result["report"]
        if result_status == 0:  # 获取完结状态的信息
            break

        sleep(100 / 1000)
        timeout_in_action -= 200
        params["timeout"] = timeout_in_action

    return report


def helper_get_data_from_exec_reports(
    account_id, sid, event, timeout_in_action, filled_vol
):
    exec_reports = None

    while timeout_in_action > 0:
        helper_reset_event(event)
        result = csv_get_exec_report_data_by_sid(account_id, sid)
        if result is None:
            logger.warning("exec report file not found of this account: %s", account_id)
            return None

        status = result["result"]
        if status != -1:  # save result, then retry
            exec_reports = result["reports"]

        if status == 0:  # 收集到了至少一条数据
            helper_get_exec_reports_by_sid(exec_reports, event)
            if event.status == OrderStatus.ALL_TRANSACTIONS:
                if event.volume == event.filled:  # 已完成的委托，但是成交数据不全，继续等待
                    break  # 结束循环

            if event.status == OrderStatus.PARTIAL_TRANSACTION:
                if event.filled >= filled_vol:  # 部分成交的情况下，至少要大于委托状态里面的成交量
                    break

        sleep(100 / 1000)
        timeout_in_action -= 200

    return exec_reports


def helper_get_orders_from_status_change_by_sidlist(account_id, sid_list):
    reports = {}

    # 默认等待2000毫秒
    timeout_in_action = 2000
    while timeout_in_action > 0:
        result = csv_get_order_status_change_data_by_sidlist(account_id, sid_list)
        if result is None:
            logger.warning(
                "order status change file not found of this account: %s", account_id
            )

        result_status = result["result"]
        if result_status != -1:  # 保存查询到的结果
            reports = result["reports"]

        if result_status == 0:  # 获取完结状态的信息
            break

        sleep(100 / 1000)
        timeout_in_action -= 200

    return reports
