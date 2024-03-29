from enum import Enum
from functools import wraps
from typing import Dict, List, Union

import cfg4py


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


def calculate_timeout_in_ms(
    timeout: float, min_val: float = 0.5, default_val: float = 2
) -> int:
    """计算超时参数

    Args:
        timeout (float): 用户传入的超时秒数
        min_val (float): 最小的秒数
        default_val (float): 默认的秒数

    Returns:
        int: 返回计算好的毫秒数
    """

    if timeout is None:
        return int(default_val * 1000)

    if timeout < min_val:
        return int(min_val * 1000)
    if timeout > 60:
        return 60 * 1000

    return int(timeout * 1000)
