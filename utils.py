"""
日志、限速、缓存等工具
"""
import logging
import os
from pathlib import Path
from typing import Any, Optional

# ------------- 日志等级 -------------
env_file = Path(".env")
LOG_LEVEL = "INFO"
if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("LOG_LEVEL="):
            _, level = line.split("=", 1)
            LOG_LEVEL = level.strip()
            break

# ------------- logger -------------
def setup_logger(name: str = "summarizer") -> logging.Logger:
    """返回已配置好的 logger 实例（带控制台 handler）"""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.getLevelName(LOG_LEVEL))
    handler = logging.StreamHandler()
    fmt = "[%(asctime)s] %(levelname)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    return logger