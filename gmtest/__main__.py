# 本文件为冒烟测试
import sys

#!/usr/bin/env python
"""Tests for `gmtrader` package."""
# pylint: disable=redefined-outer-name

import sys
import uuid

import httpx

cid = str(uuid.uuid4())

headers = {
    "Authorization": "84ae0899-7a8d-44ff-9983-4fa7cbbc424b",
    "Account-ID": "780dc4fda3d0af8a2d3ab0279bfa48c9"
}

_url_prefix = "http://192.168.100.100:9000/"

def get_balance():
    r = httpx.post(_url_prefix + "balance", headers=headers)
    if r.status_code == 200:
        print("\n------ 账户资金信息 ------")
        print(r.json())

def get_positions():
    r = httpx.post(_url_prefix + "positions", headers=headers)
    
    if r.status_code == 200:
        print("\n----- 持仓信息 ------")
        print(r.json())

def buy():
    r = httpx.post(_url_prefix + "buy", headers=headers, json={
        "security": "000001",
        "price": 13,
        "volume": 100,
        "cid": cid,
        "timeout": 5
    }, timeout=30)

    if r.status_code == 200:
        print("\n ------ 买入成交回报 ------")
        print(r.json())
    else:
        print("买入失败:", r.status_code, r.json())

def market_sell():
    r = httpx.post(_url_prefix + "market_sell", headers=headers, json = {
        "security": "000001",
        "volume": 100,
        "cid": cid
    })

def run(account, token, server, port):
    global headers, url

    url = f"http://{server}:{port}/"
    headers = {
        "Authorization": token,
        "Account-ID": account
    }

    # get_balance()
    # get_positions()
    # buy()
    market_sell()



if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("------- 帮助 --------")
        print("python -m tests.test run account token server port")
        print("如果不传入server和port，默认为localhost和9000")
        sys.exit(0)
    
    elif len(sys.argv) == 3:
        account, token = sys.argv[-2:]
        server = 'localhost'
        port = 9000
    elif len(sys.argv) == 4:
        account, token, server = sys.argv[-3:]
        port = 9000
    elif len(sys.argv) == 5:
        account, token, server, port = sys.argv[-4:]

    run(account, token, server, port)
