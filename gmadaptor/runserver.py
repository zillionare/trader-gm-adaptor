# -*- coding: utf-8 -*-
import logging
import os
from os import path, sys

import cfg4py
from cfg4py.config import Config
from gmadaptor.gmclient.wrapper import gm_client_wrapper_start
from gmadaptor.httpserver.server import server_start

logger = logging.getLogger(__name__)


def init_logger():
    LOG_FORMAT = (
        r"%(asctime)s %(name)s %(levelname)s %(filename)s[line:%(lineno)d] %(message)s"
    )
    DATE_FORMAT = r"%Y-%m-%d  %H:%M:%S %a"
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT)


def add_log_file_handler(filename: str, loglevel: int):
    fh = logging.FileHandler(filename, mode="a+")
    fh.setLevel(loglevel)

    LOG_FORMAT = (
        r"%(asctime)s %(name)s %(levelname)s %(filename)s[line:%(lineno)d] %(message)s"
    )
    DATE_FORMAT = r"%Y-%m-%d  %H:%M:%S %a"
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    fh.setFormatter(formatter)

    logger.addHandler(fh)


def update_config_folder(folder: str) -> int:
    sys.path.insert(0, folder)

    # check if configuration folder exists
    if not os.path.exists(folder):
        return -1

    cfg4py.init(folder, False)

    return 0


def start():
    init_logger()
    logger.debug("trader-gm-adpator starts")

    config_dir = path.normpath(path.join(path.dirname(__file__), "config"))
    print(config_dir)

    if update_config_folder(config_dir) != 0:
        logger.error("configuration file cannot be found or invalid")
        return

    server_config = cfg4py.get_instance()

    loglevel = server_config.log_level
    logfile = path.normpath(path.join(path.dirname(__file__), "gm-adaptor.log"))
    add_log_file_handler(logfile, loglevel)

    logger.info("launch gm client")
    gm_client_wrapper_start()

    logger.info("launch mock server")
    server_info = server_config.server_info
    server_start(server_info.port)


if __name__ == "__main__":
    start()
