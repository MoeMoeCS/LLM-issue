"""
日志、限速、缓存等工具
"""
import logging
from pathlib import Path
from typing import Any

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


# ------------- 内存缓存 -------------
_cache: dict[str, Any] = {}


def get_cache(key: str) -> Any | None:
    """根据 key 读取缓存值，不存在返回 None"""
    return _cache.get(key)


def set_cache(key: str, value: Any) -> None:
    """将 key-value 写入内存缓存"""
    _cache[key] = value