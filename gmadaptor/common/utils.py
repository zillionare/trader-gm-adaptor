def math_round(x: float, digits: int):
    if x < 0:
        return int(x * (10**digits) - 0.5) / (10**digits)
    else:
        return int(x * (10**digits) + 0.5) / (10**digits)


def safe_float(val: str):
    if val is None or len(val) == 0:
        return 0.0
    else:
        return float(val)


def safe_int(val: str):
    if val is None or len(val) == 0:
        return 0
    else:
        return int(val)


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


def get_stock_location(stock: str):
    # SHSE.xxx, SZSE.xxx -> 1, 2
    (stock_num, sec_name) = stock.split(".")
    if sec_name.find("SHSE") != -1:
        return 1  # shanghai
    elif sec_name.find("SZSE") != -1:
        return 2
    return None
