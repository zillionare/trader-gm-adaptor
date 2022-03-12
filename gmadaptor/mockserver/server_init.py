# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import logging
import os
import sys
from os import path

import cfg4py
from cfg4py.config import Config
from sanic import Sanic

from gmadaptor.mockserver.route_map import initialize_blueprint

logger = logging.getLogger(__name__)

app = Sanic("trader-gm-adaptor")


def server_start(port: int = 9000) -> int:
    """_summary_

    this is am example

    Examples:
        >>> sum(1, 2)
        3

    Raises:

    Args:
        port (int, optional): _description_. Defaults to 9001.

    Returns:
        int: _description_
    """
    initialize_blueprint(app)
    print("server initialized")
    app.run(host="0.0.0.0", port="9000")
