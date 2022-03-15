from enum import Enum
from functools import wraps
from typing import Dict, List, Union

import cfg4py
from cfg4py.config import Config
from expiringdict import ExpiringDict


def check_request_token(access_token):
    server_config = cfg4py.get_instance()
    if access_token != server_config.server_info.access_token:
        return False

    return True


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
