# -*- coding: utf-8 -*-
import logging
import os

from sanic import Blueprint, Sanic, response, request
from sanic.exceptions import ServerError

import gmtrader.gmclient_wrapper.handlers as handler
from gmtrader.mockserver.helper import make_response, check_request_token, check_duplicated_request
from gmtrader.gmclient.wrapper_init import check_gm_client_account



logger = logging.getLogger(__name__)
bp_gm_adaptor = Blueprint("gmclient", url_prefix="/gmclient/v1", strict_slashes=False)


@bp_gm_adaptor.middleware("request")
async def validate_request(request: request):
    """check token and duplicated request"""

    is_authenticated = check_request_token(request)
    if not is_authenticated:
        return response.json(make_response(401, "invalid access token"), 401)

    duplicated = check_duplicated_request(request)
    if duplicated:
        return response.json(make_response(401, "duplicated request"), 401)

    if request.method == 'POST':
        account = request.json.get('account_id')
        if (account is not None) and (not check_gmtrade_account(account)):
            return response.json(make_response(401, "invalid account id"), 401)


@bp_gm_adaptor.route("/", methods=["GET"])
async def bp_gm_adaptor_default_route(request):
    return response.text("gm trader mock server")


@bp_gm_adaptor.route("/balance", methods=["POST"])
async def bp_mock_get_balance(request):
    account_id = request.json.get("account_id")
    print(f"balance: {account_id}")

    cash = handler.wrapper_get_balance(account_id)
    mycash = gmtrade_cash(cash)
    return response.json(make_response(0, "OK", mycash.toDict()))


@bp_gm_adaptor.route("/positions", methods=["POST"])
async def bp_mock_get_positions(request):
    account_id = request.json.get("account_id")
    poses = handler.wrapper_get_positions(account_id)

    pos_list = []
    for pos in poses:
        pos_list.append(gmtrade_position(pos).toDict())

    return response.json(make_response(0, "OK", pos_list))


@bp_gm_adaptor.route("/buy", methods=["POST"])
async def bp_mock_buy(request):
    account_id = request.json.get("account_id")
    request_id = request.headers.get("Request-ID")
    symbol = request.json.get("security")
    price = request.json.get("price")
    volume = request.json.get("vloume")

    result = handler.wrapper_buy(account_id, symbol, price, volume)[0]

    # we can check result.status if this entrust success
    return response.json(
        make_response(0, "OK", {"request_id": request_id, "cid": result.cl_ord_id})
    )


@bp_gm_adaptor.route("/market_buy", methods=["POST"])
async def bp_mock_market_buy(request):
    """掘金仿真交易API支持市价成交，因此无需指定限价

    Args:
        request (_type_): _description_

    Returns:
        _type_: _description_
    """
    account_id = request.json.get("account_id")
    request_id = request.headers.get("Request-ID")
    symbol = request.json.get("security")
    #price = request.json.get("price")
    volume = request.json.get("vloume")

    result = handler.wrapper_market_buy(account_id, symbol, volume)[0]

    # we can check result.status if this entrust success
    return response.json(
        make_response(0, "OK", {"request_id": request_id, "cid": result.cl_ord_id})
    )


@bp_gm_adaptor.route("/sell", methods=["POST"])
async def bp_mock_sell(request):
    account_id = request.json.get("account_id")
    request_id = request.headers.get("Request-ID")
    symbol = request.json.get("security")
    price = request.json.get("price")
    volume = request.json.get("vloume")

    result = handler.wrapper_sell(account_id, symbol, price, volume)[0]

    # we can check result.status if this entrust success
    return response.json(
        make_response(0, "OK", {"request_id": request_id, "cid": result.cl_ord_id})
    )


@bp_gm_adaptor.route("/market_sell", methods=["POST"])
async def bp_mock_market_sell(request):
    account_id = request.json.get("account_id")
    request_id = request.headers.get("Request-ID")
    symbol = request.json.get("security")
    #price = request.json.get("price")
    volume = request.json.get("vloume")

    result = handler.wrapper_market_sell(account_id, symbol, volume)[0]

    # we can check result.status if this entrust success
    return response.json(
        make_response(0, "OK", {"request_id": request_id, "cid": result.cl_ord_id})
    )


@bp_gm_adaptor.route("/today_entrusts", methods=["POST"])
async def bp_mock_get_today_entrusts(request):
    account_id = request.json.get("account_id")
    request_id = request.headers.get("Request-ID")

    orders = handler.wrapper_get_today_entrusts(account_id)

    rpt_list = []
    for order in orders:
        rpt_list.append(gmtrade_order(order, request_id).toDict())

    return response.json(make_response(0, "OK", rpt_list))


@bp_gm_adaptor.route("/today_trades", methods=["POST"])
async def bp_mock_get_today_trades(request):
    account_id = request.json.get("account_id")
    request_id = request.headers.get("Request-ID")

    reports = handler.wrapper_get_today_trades(account_id)

    rpt_list = []
    for report in reports:
        rpt_list.append(gmtrade_exec_report(report, request_id).toDict())

    return response.json(make_response(0, "OK", rpt_list))


@bp_gm_adaptor.route("/cancel_entrust", methods=["POST"])
async def bp_mock_cancel_entrust(request):
    account_id = request.json.get("account_id")
    symbol = request.json.get("security")
    order_id = request.json.get("order_id")

    handler.wrapper_cancel_enturst(account_id, symbol, order_id)
    return response.json(make_response(0, "OK"))


@bp_gm_adaptor.route("/cancel_all_entrusts", methods=["POST"])
async def bp_mock_cancel_all_entrusts(request):
    account_id = "145be423-a021-11ec-8e33-00163e0a4100"

    handler.wrapper_cancel_all_enturst(account_id)
    return response.json(make_response(0, "OK"))


def initialize_blueprint(app: Sanic):
    """initialize sanic server blueprint

    Args:
        app (Sanic): instance of this sanic server
    """
    
    app.blueprint(bp_gm_adaptor)

    print("blueprint v1 added")
