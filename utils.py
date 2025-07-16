"""
日志、限速、缓存等工具
"""
import logging
import os
from pathlib import Path
from typing import Any, Optional

from cache import Cache

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

# ------------- 缓存实例 -------------
_cache = Cache(
    db_path=os.getenv("CACHE_DB_PATH", ".cache/cache.db"),
    max_memory_items=int(os.getenv("CACHE_MAX_MEMORY_ITEMS", "1000")),
    cleanup_interval=int(os.getenv("CACHE_CLEANUP_INTERVAL", "3600")),
)

def get_cache(key: str) -> Any | None:
    """根据 key 读取缓存值，不存在返回 None"""
    return _cache.get(key)

def set_cache(key: str, value: Any, expire_in: int = 86400) -> None:
    """
    将 key-value 写入缓存
    
    Args:
        key: 缓存键
        value: 要缓存的值
        expire_in: 过期时间（秒），默认1天
    """
    _cache.set(key, value, expire_in)

def delete_cache(key: str) -> None:
    """删除指定的缓存项"""
    _cache.delete(key)

def clear_cache() -> None:
    """清空所有缓存"""
    _cache.clear()