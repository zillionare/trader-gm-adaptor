# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import logging

logger = logging.getLogger(__name__)


def stockcode_to_joinquant(stock: str):
    # SHSE, SZSE -> XSHG, XSHE
    (sec_name, stock_num) = stock.split(".")
    if sec_name.find("SHSE") != -1:
        return f"{stock_num}.XSHG"
    elif sec_name.find("SZSE") != -1:
        return f"{stock_num}.XSHE"
    return stock


def stockcode_to_myquant(stock: str):
    # XSHG, XSHE -> SHSE, SZSE
    (stock_num, sec_name) = stock.split(".")
    if sec_name.find("XSHG") != -1:
        return f"SHSE.{stock_num}"
    elif sec_name.find("XSHE") != -1:
        return f"SZSE.{stock_num}"
    return stock


def wrapper_get_balance(account_id: str):
    # 查询账户资金，返回cash结构
    cash = get_cash(account=account_id)
    print(f"get_cash cash\n{cash}")
    return cash


def wrapper_get_positions(account_id: str):
    # 获取登录账户的持仓，如登录多个账户需要指定账户ID
    #poses = get_positions(account=account_id)
    #print(f"get_positions\n{poses}")
    #return poses


def wrapper_buy(account_id: str, security: str, price: float, volume: int):
    new_code = stockcode_to_myquant(security)
    """
    data = order_volume(
        account=account_id,
        symbol=new_code,
        volume=volume,
        price=price,
        side=OrderSide_Buy,
        order_type=OrderType_Limit,
        position_effect=PositionEffect_Open,
    )
    print(f"buy\n{data}")

    return data
    """


def wrapper_market_buy(
    account_id: str, security: str, price: float, volume: int, limit_price: float = None
):
    new_code = stockcode_to_myquant(security)
    """
    data = order_volume(
        account=account_id,
        symbol=new_code,
        volume=volume,
        side=OrderSide_Buy,
        order_type=OrderType_Market,
        position_effect=PositionEffect_Open,
    )
    print(f"market price buy\n{data}")

    return data
    """


def wrapper_sell(account_id: str, security: str, price: float, volume: int):
    new_code = stockcode_to_myquant(security)
    """
    data = order_volume(
        account=account_id,
        symbol=new_code,
        volume=volume,
        price=price,
        side=OrderSide_Sell,
        order_type=OrderType_Limit,
        position_effect=PositionEffect_Close,
    )
    print(f"sell\n{data}")

    return data
    """


def wrapper_market_sell(
    account_id: str, security: str, volume: int, limit_price: float = None
):
    new_code = stockcode_to_myquant(security)
    """
    data = order_volume(
        account=account_id,
        symbol=new_code,
        volume=volume,
        side=OrderSide_Sell,
        order_type=OrderType_Market,
        position_effect=PositionEffect_Close,
    )
    print(f"market price sell\n{data}")

    return data
    """


def wrapper_get_today_entrusts(account_id: str):
    """
    orders1 = get_orders(account=account_id)
    print(f"get_orders:\n{orders1}")

    orders2 = get_unfinished_orders(account=account_id)
    print(f"get_unfinished_orders:\n{orders2}")

    return orders1 + orders2
    """


def wrapper_cancel_enturst(account_id: str, security: str, order_id: str):
    # example from official website, at least cl_ord_id must be provided
    # order_1 = {'symbol': 'SHSE.600000', 'cl_ord_id': 'cl_ord_id_1', 'price': 11, 'side': 1, 'order_type':1 }
    order1 = {
        "account_id": account_id,
        "symbol": stockcode_to_myquant(security),
        "cl_ord_id": order_id,
    }
    orders = [order1]
    #order_cancel(wait_cancel_orders=orders)


def wrapper_cancel_all_enturst(account_id: str):
    #order_cancel_all(account=account_id)
    pass


def wrapper_get_today_trades(account_id: str):
    """
    reports = get_execution_reports(account=account_id)
    print(f"all reports:\n{reports}")
    return reports
    """
