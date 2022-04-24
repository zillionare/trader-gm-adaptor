# -*- coding: utf-8 -*-
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from os import path, sys

import cfg4py
from cfg4py.config import Config
from gmadaptor.gmclient.wrapper import gm_client_wrapper_start
from gmadaptor.httpserver.server import server_start

logger = logging.getLogger(__name__)


def get_config_dir():
    current_dir = os.getcwd()

    if cfg4py.envar in os.environ and os.environ[cfg4py.envar] == "DEV":
        module_dir = path.dirname(__file__)
        return path.normpath(path.join(module_dir, "config"))
    else:
        return path.normpath(path.join(current_dir, "config"))


def init_config():
    config_dir = get_config_dir()
    print("config dir:", config_dir)

    try:
        cfg4py.init(config_dir, False)
    except Exception as e:
        print(e)
        os._exit(1)

    return 0


def init_log_path(log_dir):
    if os.path.exists(log_dir):
        return 0

    try:
        os.makedirs(log_dir)
    except Exception as e:
        print(e)
        exit("failed to create log folder")

    return 0


def init_logger(filename: str, loglevel: int):
    LOG_FORMAT = r"%(asctime)s %(levelname)s %(filename)s[line:%(lineno)d] %(message)s"
    DATE_FORMAT = r"%Y-%m-%d  %H:%M:%S %a"

    fh = TimedRotatingFileHandler(
        filename, when="D", interval=1, backupCount=7, encoding="utf-8"
    )
    fh.setLevel(loglevel)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    fh.setFormatter(formatter)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(loglevel)
    console.setFormatter(formatter)

    logging.basicConfig(
        level=loglevel,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[console, fh],
    )


def start():
    current_dir = os.getcwd()
    print("current dir:", current_dir)

    init_config()
    server_config = cfg4py.get_instance()

    loglevel = server_config.log_level
    log_dir = path.normpath(os.path.join(current_dir, "logs"))
    init_log_path(log_dir)

    logfile = path.normpath(path.join(log_dir, "server.log"))
    init_logger(logfile, loglevel)

    logger.info("launch gm client wrapper ...")
    rc = gm_client_wrapper_start()
    if rc != 0:
        logger.error("failed to launch gm client wrapper")
        os._exit(1)

    logger.info("launch http server ...")
    server_info = server_config.server_info
    server_start(server_info.port)


if __name__ == "__main__":
    start()
