def math_round(x: float, digits: int):
    """由于浮点数的表示问题，很多语言的round函数与数学上的round函数不一致。下面的函数结果与数学上的一致。

    Args:
        x: 要进行四舍五入的数字
        digits: 小数点后保留的位数

    """
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
