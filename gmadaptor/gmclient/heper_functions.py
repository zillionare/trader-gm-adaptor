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
from gmadaptor.gmclient.csvdata import GMCash, GMExecReport, GMOrderReport, GMPosition


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
    comission: 0.03  # 券商佣金，万分之三
    stamp_duty: 0.1 # 印花税，千分之一
    transfer_fee: 0.002 # 过户费，万分之0.2
    minimum_cost: 5.0 # 最低佣金
    """
    comission = amount * (fees_info.comission / 100)
    if comission < fees_info.minimum_cost:
        comission = fees_info.minimum_cost
    transfer_fee = amount * (fees_info.transfer_fee / 100)

    stamp_duty = 0
    if order_side == 2:
        stamp_duty = amount * (fees_info.stamp_duty / 100)

    return comission + transfer_fee + stamp_duty


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
