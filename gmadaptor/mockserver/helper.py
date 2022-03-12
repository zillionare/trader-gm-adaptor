from enum import Enum
from functools import wraps
from typing import Dict, List, Union
import cfg4py
from cfg4py.config import Config
from expiringdict import ExpiringDict
from sanic import Sanic, response, request

seen_requests = ExpiringDict(max_len=1000, max_age_seconds=10 * 60)

def check_request_token(request):
    account_token = request.headers.get("Authorization")
    server_config = cfg4py.get_instance()

    if account_token != server_config.server_info.access_token:
        return False
    
    return True


def check_duplicated_request(request):
    request_id = request.headers.get("Request-ID")
    return False
    
    if request_id in seen_requests:
        return True

    seen_requests[request_id] = True
    return False


def make_response(
    err_code: Union[Enum, int], err_msg: str = None, data: Union[dict, list] = None
):
    if err_msg is None:
        err_msg = str(err_code)

    return {
        "status": err_code if isinstance(err_code, int) else err_code.value,
        "msg": err_msg,
        "data": data,
    }
