# 本文件为冒烟测试
import sys
import time

#!/usr/bin/env python
"""Tests for `gmtrader` package."""
# pylint: disable=redefined-outer-name

import sys
import uuid
from typing import Optional

import httpx

headers = {
    "Authorization": "84ae0899-7a8d-44ff-9983-4fa7cbbc424b",
    "Account-ID": "eee2dcd849adafb04ac1981378b45e05"
}

_url_prefix = "http://192.168.100.100:9000/"

def get_balance():
    r = httpx.post(_url_prefix + "balance", headers=headers)
    resp = r.json()
    if r.status_code == 200 and resp['status'] == 0:
        print("\n------ 账户资金信息 ------")
        print(resp["data"])

def get_positions():
    r = httpx.post(_url_prefix + "positions", headers=headers)
    
    resp = r.json()
    if r.status_code == 200 and resp['status'] == 0:
        print("\n----- 持仓信息 ------")
        print(resp["data"])

def buy(code: Optional[str]=None):
    cid = str(uuid.uuid4())
    r = httpx.post(_url_prefix + "buy", headers=headers, json={
        "security": code or "000572.XSHE",
        "price": 13,
        "volume": 100,
        "cid": cid,
        "timeout": 1
    })

    print("\n------ 限价委买 ------")
    print(r.json())
    return cid

def market_buy():
    cid = str(uuid.uuid4())
    r = httpx.post(_url_prefix + "market_buy", headers=headers, json={
        "security": "000572.XSHE",
        "volume": 100,
        "cid": cid,
        "timeout": 1
    })

    resp = r.json()
    if r.status_code == 200 and resp["status"] == 0:
        print("\n------ 市价委买成功 ------")
        print(resp["status"], resp["msg"], resp["data"])
        buy_entrust_no = resp["data"]["entrust_no"]
        assert cid == buy_entrust_no
        print(f"等待两秒，查询买入是否成功。")
        time.sleep(2)
        
        r = httpx.post(_url_prefix + "today_entrusts", headers=headers, json = {
            "entrust_no": [cid],
            "timeout": 1
        })

        resp = r.json()
        print(resp)
    else:
        print("\n------ 市价委买失败 ------", r.status_code, resp)


def sell():
    cid = str(uuid.uuid4())

    r = httpx.post(_url_prefix + "sell", headers=headers, json={
        "security": "000001.XSHE",
        "price": 10,
        "volume": 100,
        "cid": cid,
        "timeout": 1
    })

    resp = r.json()
    if r.status_code == 200 and resp["status"] == 0:
        print("\n------ 限价委卖成功 ------")
        data = resp["data"]
        print(data)
        sell_entrust_no = data["entrust_no"]
    else:
        print("\n------ 卖出失败 ------", r.status_code, resp)

def market_sell():
    cid = str(uuid.uuid4())
    r = httpx.post(_url_prefix + "market_sell", headers=headers, json = {
        "security": "000001.XSHE",
        "volume": 100,
        "cid": cid
    })

    resp = r.json()
    if r.status_code == 200 and resp["status"] == 0:
        print("\n ------ 市价委卖成功 ------")
        print(resp["data"])
    else:
        print(resp)

def cancel_entrust():
    cid = buy("018014.XSHE")

    r = httpx.post(_url_prefix + "cancel_entrust", headers=headers, json = {
        "entrust_no": cid,
        "timeout": 1
    })

    resp = r.json()
    print(resp["status"], resp["msg"], resp["data"])

def today_entrusts():
    r = httpx.post(_url_prefix + "today_entrusts", headers=headers, json = {
        "entrust_no": [],
        "timeout": 1
    })

    resp = r.json()
    print("\n------ 当日委托 ------")
    print(resp["status"], resp["msg"], resp['data'])

def run(account, token, server, port):
    global headers, url

    url = f"http://{server}:{port}/"
    headers = {
        "Authorization": token,
        "Account-ID": account
    }

    get_balance()
    get_positions()
    buy()
    market_buy()
    cancel_entrust()

    market_sell()
    today_entrusts()



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
