import asyncio
import datetime
import logging
from os import path
from time import sleep

import cfg4py

from gmadaptor.common.types import OrderSide, OrderStatus, OrderType, TradeEvent
from gmadaptor.common.utils import math_round, stockcode_to_joinquant
from gmadaptor.gmclient.csv_utils import csv_get_order_status_change_data_by_sidlist
from gmadaptor.gmclient.csvdata import GMOrderReport
from gmadaptor.gmclient.wrapper import get_gm_out_csv_order_status_change

logger = logging.getLogger(__name__)


def helper_init_trade_event(trade_info: dict) -> TradeEvent:
    """如果从状态变化文件读取不到数据，返回下面的默认值"""
    security = trade_info["security"]
    volume = trade_info["volume"]
    price = trade_info["price"]
    order_side = trade_info["order_side"]
    order_type = trade_info["order_type"]
    sid = trade_info["cid"]

    event = TradeEvent(
        security,  # z trade server传过来的代码，已经按照聚宽格式化
        price,  # 委托价格
        volume,
        order_side,
        order_type,
        datetime.datetime.now(),
        sid,
        OrderStatus.SUBMITTED,
        0.0,  # avg price
        0,  # filled
        "",  # order id
        0,  # trade fees
        "",  # reject detail
        datetime.datetime.now(),  # recv at
    )

    return event


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
        0.0,  # avg price
        0,  # filled
        order_status_record.order_id,
        0,  # trade fees
        order_status_record.rej_detail,
        order_status_record.recv_at,
    )
    return event


def helper_calculate_trade_fees(is_shex, amount, fees_info, order_side, is_sim):
    """交易费用计算
    commission: 2.5  # 券商佣金，万分之2.5
    stamp_duty: 10 # 印花税，千分之一
    transfer_fee: 0.1 # 过户费，万分之0.1/0.2，政策会调整
    minimum_cost: 5.0 # 最低佣金
    掘金客户端无印花税选项，因此，不能分开计算，佣金合并印花税
    """
    stamp_duty = 0
    if is_sim:  # 模拟盘无过户费，佣金和印花税合并计算，逐笔成交均计算
        commission = math_round(amount * fees_info.commission / 10000, 2)
        if order_side == 2:
            commission = math_round(
                amount * (fees_info.commission + fees_info.stamp_duty) / 10000, 2
            )
        if commission < fees_info.minimum_cost:
            commission = fees_info.minimum_cost
        return commission
    else:  # 实盘需要对照交割单修正，佣金按照委托为单位，过户费分上证和深证，后者不收取
        if order_side == 2:
            stamp_duty = math_round(amount * fees_info.stamp_duty / 10000, 2)
        if is_shex:
            transfer_fee = math_round(amount * fees_info.transfer_fee / 10000, 2)
        else:
            transfer_fee = 0  # 深证暂时不收取过户费
        return math_round(transfer_fee + stamp_duty, 2)


def helper_calculate_trade_fees_for_real(total_amount, fees_info):
    """实盘券商佣金计算
    commission: 2.5  # 券商佣金，万分之2.5
    minimum_cost: 5.0 # 最低佣金
    """
    commission = math_round(total_amount * fees_info.commission / 10000, 2)
    if commission < fees_info.minimum_cost:
        commission = fees_info.minimum_cost
    return commission


# 更新读取到的委托交易信息（执行回报文件中的数据）
def helper_sum_exec_reports_by_sid(exec_reports, event: TradeEvent):
    server_config = cfg4py.get_instance()
    trade_fees_info = server_config.gm_info.trade_fees
    is_sim = server_config.gm_info.fake
    is_shex = False
    if event.code.startswith("60"):
        is_shex = True

    total_volume = 0
    total_amount = 0.0  # 总资金量
    total_commission = 0  # 总手续费
    recv_at = None  # 最后完成交易的时间

    for exec_rpt in exec_reports:  # 从执行回报中取详细数据
        total_volume += exec_rpt.volume
        # 价格从CSV读取时已四舍五入，对金额再次四舍五入
        amount = math_round(exec_rpt.volume * exec_rpt.price, 2)
        total_amount += amount
        total_commission += helper_calculate_trade_fees(
            is_shex,
            amount,
            trade_fees_info,
            exec_rpt.order_side,
            is_sim,
        )
        recv_at = exec_rpt.recv_at

    if not is_sim:  # 实盘针对委托计算佣金
        commission = helper_calculate_trade_fees_for_real(total_amount, trade_fees_info)
        total_commission += commission

    # 平均价格的计算暂时不纳入手续费
    if total_volume == 0:
        event.avg_price = 0
    else:
        # 平均价格不能四舍五入，否则会导致计算的结果不准确
        event.avg_price = total_amount / total_volume

    event.filled = total_volume
    # 汇总后的数据最后进行一次四舍五入
    event.filled_amount = math_round(total_amount, 2)
    event.trade_fees = math_round(total_commission, 2)

    if recv_at is not None:  # 更新最后的成交时间
        event.recv_at = recv_at

    if event.status == OrderStatus.ALL_TX:
        # 已完成的委托，但是成交数据不全，清除掉汇总数据，避免出错
        if event.filled > event.volume:
            logger.error("全成的委托，成交量大于委托量：%s -> %s", event.entrust_no, event.code)
            helper_reset_event(event, True)
            return -1  # 数据错误，结束尝试
        elif event.filled == event.volume:
            return 0
        else:
            logger.error("全成的委托，读取的数据不完整：%s -> %s", event.entrust_no, event.code)
            return 1  # 数据不完整，继续读取，因为超时限制，可能这是本次循环最后一次读取

    if event.status == OrderStatus.PARTIAL_TX or event.status == OrderStatus.CANCELED:
        if event.filled > event.volume:
            logger.error("部成和已撤的委托，成交量大于委托量，不正确：%s -> %s", event.entrust_no, event.code)
            helper_reset_event(event, True)
            return -1  # 已经错误，不再继续执行
        elif event.volume == event.filled:
            return 0  # 已经完成，不再继续执行，即使下次再查，数据也不会出错，只是状态纠正了
        else:
            return 1  # 数据可能不完整，可以继续尝试几次

    if event.filled != 0:
        logger.error(
            "非成交的委托成交量不为0：%s -> %s, status: %d",
            event.entrust_no,
            event.code,
            event.status,
        )
        return -1  # 服务器不处理此类委托的成交信息
    else:
        return 0


# 循环读取执行回报之前，清除掉交易信息
def helper_reset_event(event, invalid=False):
    event.avg_price = 0
    event.filled = 0
    event.trade_fees = 0
    event.filled_amount = 0
    event.recv_at = event.created_at
    event.invalid = invalid  # 标记是否为无效数据


# 从status change file中读取订单状态变化数据
# 交易不一定顺利执行完毕，因此需要在超时后判断是否完成交易
async def helper_get_order_status_changes(
    account_id: str, sid_list: list, timeout: int
):
    status_file = get_gm_out_csv_order_status_change(account_id)
    if not path.exists(status_file):
        logger.error(
            "order status change file not found (file order service not ready): %s",
            status_file,
        )
        return None

    reports = {}  # 定义成空值，避免和None冲突
    while timeout > 0:
        result = await csv_get_order_status_change_data_by_sidlist(
            status_file, sid_list
        )
        result_status = result["result"]
        if result_status != -1:  # 有任何结果先保存(-1表示没查到结果)
            reports = result["reports"]

        if result_status == 0:  # 获取完结状态的信息
            break

        await asyncio.sleep(200 / 1000)
        timeout -= 200

    if not reports:
        logger.error(
            "failed to get status change result (no results), %s, %s",
            account_id,
            sid_list,
        )
    return reports
