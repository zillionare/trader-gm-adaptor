# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import datetime
import logging
import os
from os import path
from threading import Lock

import cfg4py
from cfg4py.config import Config

logger = logging.getLogger(__name__)

gm_out_dir = ""
account_list = {}


def check_gm_account(account_id: str):
    if account_id in account_list.keys():
        return True
    else:
        logger.warning("account id not found in account list: %s", account_id)
        return False


def get_gm_out_csv_cash(account_id: str):
    if account_id in account_list.keys():
        return path.normpath(path.join(gm_out_dir, account_id, "cash.csv"))
    else:
        logger.warn("account id not found in account list: %s", account_id)
        return None


def get_gm_out_csv_position(account_id: str):
    if account_id in account_list.keys():
        return path.normpath(path.join(gm_out_dir, account_id, "position.csv"))
    else:
        logger.warn("account id not found in account list: %s", account_id)
        return None


def get_gm_out_csv_execreport(account_id: str):
    if account_id in account_list.keys():
        return path.normpath(path.join(gm_out_dir, account_id, "execution_report.csv"))
    else:
        logger.warn("account id not found in account list: %s", account_id)
        return None


def get_gm_out_csv_orderstatus(account_id: str):
    if account_id in account_list.keys():
        return path.normpath(path.join(gm_out_dir, account_id, "order_status.csv"))
    else:
        logger.warn("account id not found in account list: %s", account_id)
        return None


# order_status_change
def get_gm_out_csv_order_status_change(account_id: str):
    if account_id in account_list.keys():
        return path.normpath(
            path.join(gm_out_dir, account_id, "order_status_change.csv")
        )
    else:
        logger.warn("account id not found in account list: %s", account_id)
        return None


def get_gm_in_csv_order(account_id: str):
    if account_id not in account_list.keys():
        logger.warn("account id not found in account list: %s", account_id)
        return None

    home = account_list[account_id][1]
    if not path.exists(home):
        logger.error(
            "input folder for account %s not exist, please check your config file", home
        )
        return None

    time1 = datetime.datetime.now()
    csvfile = "%4d%02d%02d.order.csv" % (time1.year, time1.month, time1.day)
    return path.normpath(path.join(home, csvfile))


def get_gm_in_csv_cancelorder(account_id: str):
    if account_id not in account_list.keys():
        logger.warn("account id not found in account list: %s", account_id)
        return None

    home = account_list[account_id][1]
    if not path.exists(home):
        logger.error(
            "input folder for account %s not exist, please check your config file", home
        )
        return None

    time1 = datetime.datetime.now()
    csvfile = "%4d%02d%02d.cancel_order.csv" % (time1.year, time1.month, time1.day)
    return path.normpath(path.join(home, csvfile))


def get_gm_account_info(account_id: str):
    if account_id not in account_list.keys():
        logger.warn("account id not found in account list: %s", account_id)
        return None

    return account_list[account_id]


def gm_client_wrapper_start() -> int:
    server_config = cfg4py.get_instance()
    gm_info = server_config.gm_info

    global gm_out_dir
    gm_out_dir = gm_info.gm_output
    if not path.exists(gm_out_dir):
        logger.error("output folder of this gm client not found: %s", gm_out_dir)
        return -1

    accounts = server_config.gm_info.accounts
    for account in accounts:
        acct_name = account["name"]
        acct_id = account["acct_id"]
        acct_input = account["acct_input"]
        if not path.exists(acct_input):
            logger.fatal(
                "input folder of account %s not found: %s",
                acct_id,
                acct_input,
            )
            return -1

        # each account has only 1 input folder, so we need a lock
        lock = Lock()
        account_list[acct_id] = [
            acct_name,
            acct_input,
            lock,
        ]
        logger.info(f"account added: {acct_id}, {acct_name}, {acct_input}")

    # begin processing file orders
    return 0
