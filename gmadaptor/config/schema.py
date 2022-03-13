# noqa
from typing import Optional


class Config(object):
    __access_counter__ = 0

    def __cfg4py_reset_access_counter__(self):
        self.__access_counter__ = 0

    def __getattribute__(self, name):
        obj = object.__getattribute__(self, name)
        if name.startswith("__") and name.endswith("__"):
            return obj

        if callable(obj):
            return obj

        self.__access_counter__ += 1
        return obj

    def __init__(self):
        raise TypeError("Do NOT instantiate this class")

    log_level: Optional[str] = None

    class server_info:
        fake: Optional[bool] = None

        ip: Optional[str] = None

        port: Optional[int] = None

        access_token: Optional[str] = None

    class gm_info:
        gm_output: Optional[str] = None

        class account1:
            acct_name: Optional[str] = None

            acct_id: Optional[str] = None

            acct_input: Optional[str] = None

        class account2:
            acct_name: Optional[str] = None

            acct_id: Optional[str] = None

            acct_input: Optional[str] = None
