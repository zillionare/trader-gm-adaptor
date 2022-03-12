# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import logging
import os

import cfg4py
from cfg4py.config import Config

logger = logging.getLogger(__name__)
account_id_list = []


def check_gm_client_account(account_id: str):
    if account_id in account_id_list:
        return True
    else:
        return False


def gm_client_wrapper_start() -> int:
    server_config = cfg4py.get_instance()

    """
    for name in dir(server_config.gmtrade_info):
        value = getattr(server_config.gmtrade_info, name)
        if name.startswith("user_id_"):
            user_id_list.append(value)

    set_endpoint(f"{server_name}:{server_port}")

    # set account token
    set_token(user_token)

    # 登录账户，account_id为账户ID，必填；account_alias为账号别名，选填
    userlist = []
    for userid in user_id_list:
        user = account(account_id=userid)
        userlist.append(user)
    """

    # 开始交易业务
    pass

