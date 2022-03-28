# -*- coding: utf-8 -*-
import logging
import os
from os import path, sys

import cfg4py
from cfg4py.config import Config
from gmadaptor.gmclient.wrapper import gm_client_wrapper_start
from gmadaptor.httpserver.server import server_start

logger = logging.getLogger(__name__)


def init_logger(filename: str, loglevel: int):
    LOG_FORMAT = r"%(asctime)s %(levelname)s %(filename)s[line:%(lineno)d] %(message)s"
    DATE_FORMAT = r"%Y-%m-%d  %H:%M:%S %a"

    fh = logging.FileHandler(filename, mode="a+", encoding="utf-8")
    fh.setLevel(loglevel)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    fh.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT, handlers=[fh]
    )


def start():
    config_dir = path.normpath(path.join(path.dirname(__file__), "config"))
    print(f"configuration folder: {config_dir}")

    if not os.path.exists(config_dir):
        logger.error("configuration file cannot be found or invalid")
        return

    cfg4py.init(config_dir, False)
    server_config = cfg4py.get_instance()

    loglevel = server_config.log_level
    logfile = path.normpath(path.join(path.dirname(__file__), "server.log"))
    init_logger(logfile, loglevel)
    logger.info("trader-gm-adpator starts")

    logger.info("launch gm client")
    gm_client_wrapper_start()

    logger.info("launch mock server")
    server_info = server_config.server_info
    server_start(server_info.port)


if __name__ == "__main__":
    start()
