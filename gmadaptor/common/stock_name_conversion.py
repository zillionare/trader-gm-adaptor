# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08


def stockcode_to_joinquant(stock: str):
    # SHSE, SZSE -> XSHG, XSHE
    (sec_name, stock_num) = stock.split(".")
    if sec_name.find("SHSE") != -1:
        return f"{stock_num}.XSHG"
    elif sec_name.find("SZSE") != -1:
        return f"{stock_num}.XSHE"
    return stock


def stockcode_to_myquant(stock: str):
    # XSHG, XSHE -> SHSE, SZSE
    (stock_num, sec_name) = stock.split(".")
    if sec_name.find("XSHG") != -1:
        return f"SHSE.{stock_num}"
    elif sec_name.find("XSHE") != -1:
        return f"SZSE.{stock_num}"
    return stock
