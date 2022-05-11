# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import datetime

from gmadaptor.common.name_conversion import stockcode_to_joinquant
from gmadaptor.common.utils import math_round


def datetime_conversion(timestr: str):
    # 2022-03-12T15:58:03.441803+08:00
    if timestr.find(".") != -1:
        return datetime.datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%S.%f+08:00")
    else:
        return datetime.datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%S+08:00")


class GMCash:
    account_id: str  # 掘金交易账号ID
    market_val: float  # 持仓市值
    nav: float  # 净值
    pnl: float  # 净收益
    fpnl: float  # 浮动盈亏
    frozen: float  # 持仓占用资金（期货）
    available: float  # 可用资金
    balance: float  # 资金余额
    # created_at: datetime.datetime  # 资金初始时间
    # updated_at: datetime.datetime  # 资金变更时间
    # recv_at: datetime.datetime  # 终端接收时间
    # ord_frozen: float  # 冻结资金

    def __init__(self, dict_data):
        self.account_id = dict_data["account_id"]
        self.market_val = float(dict_data["market_value(market_val)"])
        self.nav = float(dict_data["nav"])
        self.pnl = float(dict_data["pnl"])
        self.fpnl = float(dict_data["fpnl"])
        self.frozen = float(dict_data["frozen"])
        self.available = float(dict_data["available"])
        self.balance = float(dict_data["balance"])

    def toDict(self):
        return {
            "account": self.account_id,
            "available": math_round(self.available, 2),
            "pnl": math_round(self.pnl, 2),
            "total": math_round(self.nav, 2),
            "ppnl": math_round(self.pnl / (self.nav - self.pnl), 4),
            "market_value": math_round(self.market_val, 2),
        }


class GMPosition:
    account_id: str  # 掘金交易账号ID
    symbol: str  # 证券代码(市场.代码)如:SZSE.000001
    side: int  # 持仓方向 参见
    volume: int  # 总持仓量; 昨持仓量(volume-vol_today)
    vol_today: int  # 今日持仓量
    vwap: float  # 持仓均价
    # vwap_dild: float    # 摊薄持仓均价
    market_val: float  # 持仓市值
    price: float  # 当前行情价格
    fpnl: float  # 持仓浮动盈亏
    # cost: float  # 持仓成本
    avl_now: int  # 当前可平仓位(根据标的的T+N属性计算)
    # created_at: int # 建仓时间
    # updated_at: int # 仓位变更时间
    # recv_at: int    # 终端接收时间

    def __init__(self, dict_data):
        self.account_id = dict_data["account_id"]
        self.symbol = dict_data["symbol"]
        self.side = int(dict_data["side"])
        self.volume = int(dict_data["volume"])
        self.vol_today = int(dict_data["volume_today(vol_today)"])
        # 持仓均价小数位数比较多，z trade server暂时不用
        self.vwap = float(dict_data["vwap"])
        self.market_val = float(dict_data["market_value(market_val)"])
        self.price = float(dict_data["price"])
        self.fpnl = float(dict_data["fpnl"])
        self.avl_now = int(dict_data["available_now(avl_now)"])

    def toDict(self):
        return {
            "account": self.account_id,
            "code": stockcode_to_joinquant(self.symbol),
            "shares": self.volume,
            "sellable": self.avl_now + self.vol_today,  # 掘金可卖数量更新不及时，需要汇总
            "price": self.vwap,
            "market_value": math_round(self.market_val, 2),
        }


class GMOrderReport:
    """委托状态文件
    每个委托均有对应的一条记录，并且更新到最后的状态，比如成功，失败，被拒等等
    """

    account_id: str  # 掘金交易账号ID
    sid: str  # 如果该委托时由扫单服务产生的, 对应委托指令的 sid 参数. 如果该委托不是由扫单服务产生的,则为空
    # scan_name: str # 表明该委托对应的扫单名称
    cl_ord_id: str  # 委托客户端ID
    order_id: str  # 委托柜台ID
    symbol: str  # 证券代码(市场.代码)如:SZSE.000001
    order_type: int  # 委托类型 参见
    order_side: int  # 委托业务属性 参见
    status: int  # 委托状态 参见
    rej_reason: int  # 委托拒绝原因 参见
    rej_detail: str  # 委托拒绝原因描述
    price: float  # 委托价格  ----> 市价委托时，无此价格，具体价格参考执行回报文件
    volume: int  # 委托量    ----> 市价委托时，委托量保持初始数值不变
    filled_vol: int  # 已成量    ----> 市价委托时，已成交数量累积增加，直到结束
    created_at: datetime.datetime  # 委托创建时间
    # updated_at: datetime.datetime  # 委托更新时间
    # sent_at: datetime.datetime     # 委托(终端)发送时间
    recv_at: datetime.datetime  # 委托(终端)确认(状态变为已报)时间
    # filledvwap: float   #已成均价    ---->  暂时没有此字段
    # filled_amt: float   #已成金额    ---->  暂时没有此字段

    # account_id,sid,scan_name,cl_ord_id,order_id,symbol,order_type,order_business(order_biz),
    # status,ord_rej_reason(rej_reason),ord_rej_reason_detail(rej_detail),
    # price,volume,filled_volume(filled_vol),created_at,updated_at,sent_at,recv_at
    def __init__(self, dict_data):
        self.sid = dict_data["sid"]
        self.cl_ord_id = dict_data["cl_ord_id"]
        self.order_id = dict_data["order_id"]
        self.symbol = dict_data["symbol"]
        self.order_type = int(dict_data["order_type"])
        self.order_side = int(dict_data["order_business(order_biz)"])
        self.status = int(dict_data["status"])
        self.rej_reason = int(dict_data["ord_rej_reason(rej_reason)"])
        self.rej_detail = dict_data["ord_rej_reason_detail(rej_detail)"]
        self.price = math_round(float(dict_data["price"]), 2)
        self.volume = int(dict_data["volume"])
        self.filled_vol = int(dict_data["filled_volume(filled_vol)"])
        self.created_at = datetime_conversion(dict_data["created_at"])
        self.recv_at = datetime_conversion(dict_data["recv_at"])
        # 暂时不需要剩下2个时间参数

    def toDict(self):
        # 开发用途，正式接口不用此转换
        return {
            "sid": self.sid,
            "eid": self.order_id,
            "code": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "filled": self.filled_vol,
            "order_type": self.order_type,
            "order_side": self.order_side,
            "date": self.recv_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "status": self.status,
            "reason": self.rej_reason,
        }


class GMExecReport:
    """委托执行回报
    经过观察，该回报文件内的委托，都是成功状态的，
    如果是异常状态，比如被拒绝，在order status change文件中有详细的信息，
    或者在order status里面有最终的结果

    注意：此文件的更新速度比状态变化文件慢几秒中
    """

    account_id: str  # 掘金交易账号ID
    sid: str  # 如果该委托时由扫单服务产生的, 对应委托指令的 sid 参数. 如果该委托不是由扫单服务产生的,则为空
    # scan_name: str  # 表明该委托对应的扫单名称
    cl_ord_id: str  # 委托客户端ID
    order_id: str  # 委托柜台ID
    exec_id: str  # 委托回报ID
    symbol: str  # 证券代码(市场.代码)如:SZSE.000001
    order_type: int  # 委托类型 参见
    order_side: int  # 委托业务属性 参见
    rej_reason: int  # 委托拒绝原因 参见
    rej_detail: str  # 委托拒绝原因描述
    exec_type: int  # 执行回报类型 参见
    price: float  # 成交价格       ------> 市价委托情况下，此为单次成交价格
    volume: int  # 成交量         ------> 市价委托情况下，此为单次成交的数量
    created_at: datetime.datetime  # 回报创建时间
    recv_at: datetime.datetime  # 终端接收时间
    # amount: float                 # 委托成交金额   --> 暂无此字段

    # account_id,sid,scan_name,cl_ord_id,order_id,exec_id,symbol,order_type,order_business(order_biz),
    # ord_rej_reason(rej_reason),ord_rej_reason_detail(rej_detail),exec_type,price,volume,created_at,recv_at

    def __init__(self, dict_data):
        self.sid = dict_data["sid"]
        # self.scan_name = dict_data["scan_name"]
        self.cl_ord_id = dict_data["cl_ord_id"]
        self.order_id = dict_data["order_id"]
        self.exec_id = dict_data["exec_id"]
        self.symbol = dict_data["symbol"]
        self.order_type = int(dict_data["order_type"])
        self.order_side = int(dict_data["order_business(order_biz)"])
        self.rej_reason = int(dict_data["ord_rej_reason(rej_reason)"])
        self.rej_detail = dict_data["ord_rej_reason_detail(rej_detail)"]
        self.exec_type = int(dict_data["exec_type"])
        # 对价格进行指定精度处理，股票价格小数只有两位
        self.price = math_round(float(dict_data["price"]), 2)
        self.volume = int(dict_data["volume"])
        self.created_at = datetime_conversion(dict_data["created_at"])
        self.recv_at = datetime_conversion(dict_data["recv_at"])

    def toDict(self):
        # 开发用途，正式接口不用此转换
        return {
            "sid": self.sid,
            "eid": self.order_id,
            "code": self.symbol,
            "price": self.price,
            "filled": self.volume,
            "order_type": self.order_type,
            "order_side": self.order_side,
            "status": self.exec_type,
            "date": self.recv_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "reason": self.rej_reason,
        }
