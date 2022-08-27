# -*- coding: utf-8 -*-
import logging

from sanic import Blueprint, Sanic, request, response

import gmadaptor.gmclient.handlers as handler
from gmadaptor.common.types import OrderSide, OrderType
from gmadaptor.gmclient.wrapper import check_gm_account
from gmadaptor.httpserver.helper import (
    calculate_timeout_in_ms,
    check_request_token,
    make_response,
)

logger = logging.getLogger(__name__)
bp_gm_adaptor = Blueprint("gmclient", strict_slashes=False)


@bp_gm_adaptor.middleware("request")
async def validate_request(request: request):
    # check access_token first
    token = request.headers.get("Authorization")
    is_authenticated = check_request_token(token)
    if not is_authenticated:
        return response.json(make_response(401, "invalid access token"), 401)

    if request.method == "POST":
        account = request.headers.get("Account-ID")
        if account is None or (not check_gm_account(account)):
            return response.json(make_response(401, "invalid Account-ID"), 401)


@bp_gm_adaptor.route("/", methods=["GET"])
async def bp_gm_adaptor_default_route(request):
    return response.text("gm file order wrapper")


@bp_gm_adaptor.route("/balance", methods=["POST"])
async def bp_mock_get_balance(request):
    # 获取账户余额信息，主要给z trade server校正数据使用
    account_id = request.headers.get("Account-ID")
    logger.info(f"balance: account->{account_id}")

    result = await handler.wrapper_get_balance(account_id)
    if result["status"] != 200:
        logger.info(f"balance result: {result['msg']}")
        return response.json(make_response(-1, result["msg"]))

    logger.info(f"balance result: \n{result['data']}")
    return response.json(make_response(0, "OK", result["data"]))


@bp_gm_adaptor.route("/positions", methods=["POST"])
async def bp_mock_get_positions(request):
    # 获取券商端的账号持仓信息，主要给z trade server校正数据用
    account_id = request.headers.get("Account-ID")
    logger.info(f"positions: account->{account_id}")

    result = await handler.wrapper_get_positions(account_id)
    if result["status"] != 200:
        logger.info(f"positions result: {result['msg']}")
        return response.json(make_response(-1, result["msg"]))

    logger.info(f"positions result: \n{result['data']}")
    return response.json(make_response(0, "OK", result["data"]))


@bp_gm_adaptor.route("/buy", methods=["POST"])
async def bp_mock_buy(request):
    # 限价买入操作
    account_id = request.headers.get("Account-ID")
    symbol = request.json.get("security")
    price = request.json.get("price")
    volume = int(request.json.get("volume"))
    timeout = request.json.get("timeout")
    sid = request.json.get("cid", None)  # 关键参数
    timeout_in_ms = calculate_timeout_in_ms(timeout, 2, 5)
    logger.info(
        f"buy: code->{symbol}, price->{price}, volume->{volume}, timeout->{timeout_in_ms}"
    )

    if symbol is None or price is None or volume is None or sid is None:
        logger.info("parameter is empty: %s", account_id)
        return response.json(make_response(-1, "parameter cannot be empty"))

    trade_info = {
        "security": symbol,
        "volume": volume,
        "price": price,
        "order_side": OrderSide.BUY,
        "order_type": OrderType.MARKET,
        "cid": sid,
        "limit_price": 0,
    }

    result = await handler.wrapper_trade_action(account_id, [trade_info], timeout_in_ms)
    if result["status"] != 200:
        logger.info(f"buy result: {result['msg']}")
        return response.json(make_response(-1, result["msg"]))

    data = result["data"]
    logger.info(f"buy result: \n{data}")
    return response.json(make_response(0, "OK", data))


@bp_gm_adaptor.route("/market_buy", methods=["POST"])
async def bp_mock_market_buy(request):
    # 掘金文件单支持多种市价成交方式
    account_id = request.headers.get("Account-ID")
    symbol = request.json.get("security")
    volume = int(request.json.get("volume"))
    sid = request.json.get("cid", None)  # 关键参数
    if symbol is None or volume is None or sid is None:
        logger.info("parameter is empty: %s", account_id)
        return response.json(make_response(-1, "parameter cannot be empty"))

    # 市价交易暂时不用价格，及限价参数
    price = request.json.get("price")
    if price is None:  # 尽量不用None传递参数
        price = 0
    limit_price = request.json.get("limit_price")
    if limit_price is None:  # 尽量不用None传递参数
        limit_price = 0
    timeout = request.json.get("timeout")
    timeout_in_ms = calculate_timeout_in_ms(timeout, 2, 5)

    logger.info(
        f"market_buy: code->{symbol}, volume->{volume}, price->{price}, limit_price->{limit_price}, timeout->{timeout_in_ms}"
    )

    trade_info = {
        "security": symbol,
        "volume": volume,
        "price": price,
        "order_side": OrderSide.BUY,
        "order_type": OrderType.MARKET,
        "cid": sid,
        "limit_price": limit_price,
    }

    result = await handler.wrapper_trade_action(account_id, [trade_info], timeout_in_ms)
    if result["status"] != 200:
        logger.info(f"market_buy result: {result['msg']}")
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    data = result["data"]
    logger.info(f"market_buy result: \n{data}")
    return response.json(make_response(0, "OK", data))


@bp_gm_adaptor.route("/sell", methods=["POST"])
async def bp_mock_sell(request):
    account_id = request.headers.get("Account-ID")
    symbol = request.json.get("security")
    price = request.json.get("price")
    volume = int(request.json.get("volume"))
    sid = request.json.get("cid", None)  # 关键参数
    if symbol is None or price is None or volume is None or sid is None:
        logger.info("parameter is empty: %s", account_id)
        return response.json(make_response(-1, "parameter cannot be empty"))

    timeout = request.json.get("timeout")
    timeout_in_ms = calculate_timeout_in_ms(timeout, 1, 2)
    logger.info(
        f"sell: code->{symbol}, price->{price}, volume->{volume}, timeout->{timeout_in_ms}"
    )

    trade_info = {
        "security": symbol,
        "volume": volume,
        "price": price,
        "order_side": OrderSide.SELL,
        "order_type": OrderType.LIMIT,
        "cid": sid,
        "limit_price": 0,
    }
    result = await handler.wrapper_trade_action(account_id, [trade_info], timeout_in_ms)
    if result["status"] != 200:
        logger.info(f"sell result: {result['msg']}")
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    data = result["data"]
    logger.info(f"sell result: \n{data}")
    return response.json(make_response(0, "OK", data))


@bp_gm_adaptor.route("/market_sell", methods=["POST"])
async def bp_mock_market_sell(request):
    account_id = request.headers.get("Account-ID")
    symbol = request.json.get("security")
    volume = int(request.json.get("volume"))
    sid = request.json.get("cid", None)  # 关键参数
    if symbol is None or volume is None or sid is None:
        logger.info("parameter is empty: %s", account_id)
        return response.json(make_response(-1, "parameter cannot be empty"))

    price = request.json.get("price")
    if price is None:
        price = 0
    limit_price = request.json.get("limit_price")
    if limit_price is None:  # 尽量不用None传递参数
        limit_price = 0
    timeout = request.json.get("timeout")
    timeout_in_ms = calculate_timeout_in_ms(timeout, 1, 2)

    logger.info(
        f"market_sell: code->{symbol}, volume->{volume}, price->{price}, limit_price->{limit_price}, timeout->{timeout_in_ms}"
    )

    trade_info = {
        "security": symbol,
        "volume": volume,
        "price": price,
        "order_side": OrderSide.SELL,
        "order_type": OrderType.MARKET,
        "cid": sid,
        "limit_price": 0,
    }
    result = await handler.wrapper_trade_action(account_id, [trade_info], timeout_in_ms)
    if result["status"] != 200:
        logger.info(f"market_sell result: {result['msg']}")
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    data = result["data"]
    logger.info(f"market_sell result: \n{data}")
    return response.json(make_response(0, "OK", data))


@bp_gm_adaptor.route("/batch_sell", methods=["POST"])
async def bp_mock_batch_sell(request):
    account_id = request.headers.get("Account-ID")

    sell_info_list = request.json.get("sec_list", None)
    if not sell_info_list:
        logger.info("sell info list is empty: %s", account_id)
        return response.json(make_response(-1, "parameter cannot be empty"))
    if not isinstance(sell_info_list, list):
        logger.info("sell info list must be array: %s", account_id)
        return response.json(make_response(-1, "parameter is not array-like"))

    timeout = request.json.get("timeout")
    timeout_in_ms = calculate_timeout_in_ms(timeout, 1, 2)

    logger.info(f"batch_sell: timeout->{timeout_in_ms}, info list->{sell_info_list}")

    result = await handler.wrapper_trade_action(
        account_id, sell_info_list, timeout_in_ms
    )
    if result["status"] != 200:
        logger.info(f"market_sell result: {result['msg']}")
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    data = result["data"]
    logger.info(f"market_sell result: \n{data}")
    return response.json(make_response(0, "OK", data))


@bp_gm_adaptor.route("/cancel_entrust", methods=["POST"])
async def bp_mock_cancel_entrust(request):
    # 支持单个委托的撤销指令
    account_id = request.headers.get("Account-ID")
    # 掘金文件单只支持SID关联委托，其他order id不可用
    sid = request.json.get("entrust_no")
    logger.info("cancel_entrust: account->%s, entrust->%s", account_id, sid)

    if sid is None or isinstance(sid, list):
        logger.info("cancel_entrust: only 1 entrust ID list accepted")
        return response.json(make_response(400, "only 1 entrust ID list accepted"))

    result = await handler.wrapper_cancel_entursts(account_id, [sid])
    if result["status"] != 200:
        logger.info(f"cancel_entrust result: {result['msg']}")
        return response.json(make_response(-1, result["msg"]))

    datalist = result["data"]
    if len(datalist) == 0:
        logger.info("cancel_entrusts result: no results found")
        return response.json(make_response(1, "no results found"))
    else:
        values = list(datalist.values())
        item = values[0]
        logger.info(f"cancel_entrust result: \n{item}")
        return response.json(make_response(0, "OK", item))


@bp_gm_adaptor.route("/cancel_entrusts", methods=["POST"])
async def bp_mock_cancel_entrusts(request):
    # 支持多个委托的撤销指令
    account_id = request.headers.get("Account-ID")
    # 掘金文件单只支持SID关联委托，其他order id不可用
    sid_list = request.json.get("entrust_no")
    logger.info(
        "cancel_entrust: account->%s, entrust->%s, timeout->%d", account_id, sid_list
    )

    if not isinstance(sid_list, list) or len(sid_list) == 0:
        logger.info("cancel_entrusts: no entrust ID list provided")
        return response.json(make_response(400, "no entrust ID list provided"))

    result = await handler.wrapper_cancel_entursts(account_id, sid_list)
    if result["status"] != 200:
        logger.info(f"cancel_entrust result: {result['msg']}")
        return response.json(make_response(-1, result["msg"]))

    datalist = result["data"]
    if len(datalist) == 0:
        logger.info("cancel_entrusts result: no results found")
        return response.json(make_response(1, "no results found"))
    else:
        for item in datalist.keys():
            logger.info(f"cancel_entrusts result: {item}\n{datalist[item]}")
        return response.json(make_response(0, "OK", datalist))


@bp_gm_adaptor.route("/today_entrusts", methods=["POST"])
async def bp_mock_get_today_entrusts(request):
    """查询今天委托情况，可传入需要查询的委托号码清单"""
    account_id = request.headers.get("Account-ID")

    entrust_list = []
    if request.json is not None:
        entrust_list = request.json.get("entrust_no")
        # 有参数，但不是数组，非法
        if not isinstance(entrust_list, list):
            logger.info("today_entrusts: no entrust ID list provided")
            return response.json(make_response(400, "only entrust ID list acceptable"))

        logger.info(
            "today_entrusts: account->%s, entrusts->%s", account_id, entrust_list
        )
    else:
        logger.info("today_entrusts: account->%s, query all entrusts", account_id)

    result = await handler.wrapper_get_today_all_entrusts(account_id)
    if result["status"] != 200:
        logger.info(f"today_entrusts result: {result['msg']}")
        return response.json(make_response(-1, result["msg"]))

    datalist = result["data"]
    return_list = {}
    if len(entrust_list) > 0:  # 取出用户需要的委托信息
        for entrust_no in entrust_list:
            if entrust_no in datalist:
                return_list[entrust_no] = datalist[entrust_no]
    else:
        return_list = datalist

    if len(return_list) > 0:
        for item in return_list.keys():
            logger.info(f"today_entrusts result: {item}\n{return_list[item]}")
    else:
        logger.info(
            "today_entrusts result: no results found, datalist: %d", len(datalist)
        )
    return response.json(make_response(0, "OK", return_list))


def initialize_blueprint(app: Sanic):
    """initialize sanic server blueprint

    Args:
        app (Sanic): instance of this sanic server
    """

    app.blueprint(bp_gm_adaptor)
    print("blueprint v1 added")
