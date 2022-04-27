from asyncio.log import logger
from os import path
from time import sleep

import cfg4py
from gmadaptor.common.name_conversion import stockcode_to_joinquant
from gmadaptor.common.types import OrderSide, OrderStatus, OrderType, TradeEvent
from gmadaptor.gmclient.csv_utils import (
    csv_get_exec_report_data_by_sid,
    csv_get_order_status_change_data_by_sid,
    csv_get_order_status_change_data_by_sidlist,
)
from gmadaptor.gmclient.csvdata import GMOrderReport
from gmadaptor.gmclient.types import GMOrderBiz, GMOrderType
from gmadaptor.gmclient.wrapper import (
    get_gm_out_csv_execreport,
    get_gm_out_csv_order_status_change,
)


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


# 更新读取到的委托交易信息（执行回报文件中的数据）
def helper_sum_exec_reports_by_sid(exec_reports, event):
    server_config = cfg4py.get_instance()
    trade_fees = server_config.gm_info.trade_fees

    total_volume = 0
    total_amount = 0.0  # 总资金量
    total_commission = 0  # 总手续费
    recv_at = None  # 最后完成交易的时间

    for exec_rpt in exec_reports:  # 从执行回报中取详细数据
        if exec_rpt.sid == event.entrust_no:
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

    if event.status == OrderStatus.ALL_TRANSACTIONS:
        # 已完成的委托，但是成交数据不全，清除掉汇总数据，避免出错
        if event.volume != event.filled:
            logger.warning("全成的委托，读取的数据不完整: %s -> %s", event.entrust_no, event.code)
            helper_reset_event(event)
            return False  # 数据不完整，可以继续尝试几次
        else:
            return True  # 结束循环

    if event.status == OrderStatus.PARTIAL_TRANSACTION or event.status == OrderStatus.CANCEL_ALL_ORDERS:
        if event.volume < event.filled:
            logger.error("部成和已撤的委托，成交量大于委托量，不正确：%s -> %s", event.entrust_no, event.code)
            helper_reset_event(event)
            return True  # 已经错误，不再继续执行
        else:
            return False  # 数据可能不完整，可以继续尝试几次
    
    return True  # 其他情况不继续处理了


# 循环读取执行回报之前，清除掉交易信息
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


# 从status change file中读取订单状态变化数据
# 交易不一定顺利执行完毕，因此需要在超时后判断是否完成交易
def helper_get_order_status_change_data(account_id, sid, params):
    status_file = get_gm_out_csv_order_status_change(account_id)
    if not path.exists(status_file):
        logger.error("order status change file not found: %s", status_file)
        return None

    reports = []  # 定义成空值，避免和None冲突
    timeout_in_action = params["timeout"]  # 毫秒
    while timeout_in_action > 0:
        result = csv_get_order_status_change_data_by_sid(status_file, sid)
        result_status = result["result"]
        if result_status != -1:  # 保存查询到的结果，继续查看，-1代表未查询到结果
            reports.append(result["report"])

        if result_status == 0:  # 完结状态直接退出循环
            break

        sleep(200 / 1000)
        timeout_in_action -= 200
        params["timeout"] = timeout_in_action  # 保存剩下的超时计数

    return reports


# 此函数给cancel_entrust(s)使用，用来读取委托撤销的结果
def helper_get_order_status_change_by_sidlist(account_id, sid_list):
    status_file = get_gm_out_csv_order_status_change(account_id)
    if not path.exists(status_file):
        logger.error("order status change file not found: %s", status_file)
        return None

    # 默认等待2000毫秒
    timeout_in_action = 2000

    reports = {}  # 定义成空值，避免和None冲突
    while timeout_in_action > 0:
        result = csv_get_order_status_change_data_by_sidlist(status_file, sid_list)
        result_status = result["result"]
        if result_status != -1:  # 保存查询到的结果
            reports = result["reports"]

        if result_status == 0:  # 获取完结状态的信息
            break

        sleep(200 / 1000)
        timeout_in_action -= 200

    return reports


# 从执行回报文件中读取状态的详细信息，调用者：wrapper_trade_operation
def helper_get_data_from_exec_reports(account_id, sid, event, timeout_in_action):
    rpt_file = get_gm_out_csv_execreport(account_id)
    if not path.exists(rpt_file):
        logger.error("execution report file not found: %s", rpt_file)
        return None

    exec_reports = []  # 定义成空值，避免和None冲突
    while timeout_in_action > 0:
        helper_reset_event(event)  # 每次循环前，清除交易信息
        exec_reports = csv_get_exec_report_data_by_sid(rpt_file, sid)
        if len(exec_reports) > 0:  # 收集到了至少一条数据
            if helper_sum_exec_reports_by_sid(exec_reports, event):
                break

        sleep(200 / 1000)
        timeout_in_action -= 200

    return exec_reports
