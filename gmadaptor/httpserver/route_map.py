# -*- coding: utf-8 -*-
import logging
import os

from sanic import Blueprint, Sanic, request, response
from sanic.exceptions import ServerError

import gmadaptor.gmclient.handlers as handler
from gmadaptor.common.types import OrderSide
from gmadaptor.gmclient.wrapper import check_gm_account
from gmadaptor.httpserver.helper import check_request_token, make_response

logger = logging.getLogger(__name__)
bp_gm_adaptor = Blueprint("gmclient", url_prefix="/gmclient/v1", strict_slashes=False)


@bp_gm_adaptor.middleware("request")
async def validate_request(request: request):
    # check access_token first
    token = request.headers.get("Authorization")
    is_authenticated = check_request_token(token)
    if not is_authenticated:
        return response.json(make_response(401, "invalid access token"), 401)

    if request.method == "POST":
        account = request.headers.get("Account-ID")
        if account is None or not check_gm_account(account):
            return response.json(make_response(401, "invalid Account-ID"), 401)


@bp_gm_adaptor.route("/", methods=["GET"])
async def bp_gm_adaptor_default_route(request):
    return response.text("gm file order wrapper")


@bp_gm_adaptor.route("/balance", methods=["POST"])
async def bp_mock_get_balance(request):
    account_id = request.headers.get("Account-ID")
    print(f"balance: {account_id}")

    result = handler.wrapper_get_balance(account_id)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


@bp_gm_adaptor.route("/positions", methods=["POST"])
async def bp_mock_get_positions(request):
    account_id = request.headers.get("Account-ID")

    result = handler.wrapper_get_positions(account_id)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


@bp_gm_adaptor.route("/buy", methods=["POST"])
async def bp_mock_buy(request):
    account_id = request.headers.get("Account-ID")

    symbol = request.json.get("security")
    price = request.json.get("price")
    volume = request.json.get("volume")
    logger.info(f"buy, stock:{symbol}, vol:{volume}, price:{price}")

    if symbol is None or price is None or volume is None:
        logger.info("parameter is empty: %s", account_id)
        return response.json(make_response(-1, "parameter cannot be empty"))

    result = handler.wrapper_normal_trade_op(
        account_id, symbol, price, volume, OrderSide.BUY
    )
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    return response.json(make_response(0, "OK", result["data"]))


@bp_gm_adaptor.route("/market_buy", methods=["POST"])
async def bp_mock_market_buy(request):
    """掘金文件单支持多种市价成交方式

    Args:
        request (_type_): _description_

    Returns:
        _type_: _description_
    """
    account_id = request.headers.get("Account-ID")
    symbol = request.json.get("security")
    # price = request.json.get("price")
    limit_price = request.json.get("limit_price")
    volume = request.json.get("volume")

    logger.info(f"market_buy, stock:{symbol}, vol:{volume}, limit_price:{limit_price}")

    result = handler.wrapper_market_trade_op(account_id, symbol, volume, OrderSide.BUY)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    return response.json(make_response(0, "OK", result["data"]))


@bp_gm_adaptor.route("/sell", methods=["POST"])
async def bp_mock_sell(request):
    account_id = request.headers.get("Account-ID")
    symbol = request.json.get("security")
    price = request.json.get("price")
    volume = request.json.get("volume")

    logger.info(f"sell, stock:{symbol}, vol:{volume}, price:{price}")

    result = handler.wrapper_normal_trade_op(
        account_id, symbol, price, volume, OrderSide.SELL
    )
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    return response.json(make_response(0, "OK", result["data"]))


@bp_gm_adaptor.route("/market_sell", methods=["POST"])
async def bp_mock_market_sell(request):
    account_id = request.headers.get("Account-ID")

    symbol = request.json.get("security")
    # price = request.json.get("price")
    limit_price = request.json.get("limit_price")
    volume = request.json.get("volume")

    logger.info(f"market_sell, stock:{symbol}, vol:{volume}, limit_price:{limit_price}")

    result = handler.wrapper_market_trade_op(account_id, symbol, volume, OrderSide.SELL)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    return response.json(make_response(0, "OK", result["data"]))


@bp_gm_adaptor.route("/cancel_entrust", methods=["POST"])
async def bp_mock_cancel_entrust(request):
    account_id = request.json.get("account_id")
    request_id = request.headers.get("Request-ID")

    # 股票代码只作为参考用，不参与委托撤销
    symbol = request.json.get("security")
    # 掘金文件单只支持SID关联委托，其他order id不可用
    sid = request.json.get("cid")

    logger.info("cancel_enturst, account_id: %s, sid: %s", account_id, sid)

    result = handler.wrapper_cancel_enturst(account_id, symbol, sid)
    last_status = result["data"]["status"]
    return response.json(
        make_response(0, "OK", {"request_id": request_id, "status": last_status})
    )


@bp_gm_adaptor.route("/cancel_all_entrusts", methods=["POST"])
async def bp_mock_cancel_all_entrusts(request):
    account_id = request.json.get("account_id")

    logger.info("cancel_all_entrusts, account_id: %s", account_id)

    handler.wrapper_cancel_all_enturst(account_id)
    return response.json(make_response(0, "OK"))


@bp_gm_adaptor.route("/today_all_entrusts", methods=["POST"])
async def bp_mock_get_today_all_entrusts(request):
    account_id = request.json.get("account_id")
    # request_id = request.headers.get("Request-ID")

    result = handler.wrapper_get_today_all_entrusts(account_id)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    order_list = result["data"]
    return response.json(make_response(0, "OK", order_list))


@bp_gm_adaptor.route("/today_entrusts", methods=["POST"])
async def bp_mock_get_today_entrusts(request):
    account_id = request.json.get("account_id")
    # request_id = request.headers.get("Request-ID")

    result = handler.wrapper_get_today_entrusts(account_id)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    order_list = result["data"]
    return response.json(make_response(0, "OK", order_list))


@bp_gm_adaptor.route("/today_trades", methods=["POST"])
async def bp_mock_get_today_trades(request):
    account_id = request.json.get("account_id")
    # request_id = request.headers.get("Request-ID")

    result = handler.wrapper_get_today_trades(account_id)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    order_list = result["data"]
    return response.json(make_response(0, "OK", order_list))


def initialize_blueprint(app: Sanic):
    """initialize sanic server blueprint

    Args:
        app (Sanic): instance of this sanic server
    """

    app.blueprint(bp_gm_adaptor)
    print("blueprint v1 added")
