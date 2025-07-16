"""
缓存系统模块，支持内存缓存和持久化存储
"""
import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

# ------------- logger -------------
def setup_logger(name: str = "summarizer") -> logging.Logger:
    """返回已配置好的 logger 实例（带控制台 handler）"""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    fmt = "[%(asctime)s] %(levelname)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    return logger

logger = setup_logger(__name__)

class Cache:
    """
    支持内存和 SQLite 持久化的缓存系统
    
    特性：
    - 双层缓存（内存 + SQLite）
    - 支持过期时间
    - 支持最大缓存条目限制
    - 自动清理过期数据
    """
    
    def __init__(
        self,
        db_path: str = ".cache/cache.db",
        max_memory_items: int = 1000,
        cleanup_interval: int = 3600,  # 1小时清理一次过期数据
    ):
        self._memory_cache: dict[str, tuple[Any, float]] = {}  # (value, expire_time)
        self._max_memory_items = max_memory_items
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        
        # 确保缓存目录存在
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(path)
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化 SQLite 数据库表"""
        with self._get_db() as (conn, cur):
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expire_time REAL NOT NULL
                )
            """)
            conn.commit()
    
    @contextmanager
    def _get_db(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self._db_path)
        try:
            yield conn, conn.cursor()
        finally:
            conn.close()
    
    def _cleanup_expired(self, force: bool = False) -> None:
        """清理过期的缓存数据"""
        now = time.time()
        
        # 检查是否需要清理
        if not force and now - self._last_cleanup < self._cleanup_interval:
            return
        
        # 清理内存缓存
        expired_keys = [
            k for k, (_, expire_time) in self._memory_cache.items()
            if expire_time < now
        ]
        for k in expired_keys:
            del self._memory_cache[k]
        
        # 清理数据库缓存
        with self._get_db() as (conn, cur):
            cur.execute("DELETE FROM cache WHERE expire_time < ?", (now,))
            conn.commit()
        
        self._last_cleanup = now
        if expired_keys:
            logger.debug("Cleaned up %d expired cache items", len(expired_keys))
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值，如果不存在或已过期返回 None
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的值或 None
        """
        self._cleanup_expired()
        
        # 先查内存缓存
        if key in self._memory_cache:
            value, expire_time = self._memory_cache[key]
            if expire_time > time.time():
                return value
            del self._memory_cache[key]
        
        # 再查数据库缓存
        with self._get_db() as (_, cur):
            cur.execute(
                "SELECT value, expire_time FROM cache WHERE key = ?",
                (key,)
            )
            row = cur.fetchone()
            
            if row and row[1] > time.time():
                value = json.loads(row[0])
                # 提升到内存缓存
                self._memory_cache[key] = (value, row[1])
                return value
        
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        expire_in: int = 86400,  # 默认1天过期
    ) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 要缓存的值
            expire_in: 过期时间（秒），默认1天
        """
        expire_time = time.time() + expire_in
        
        # 写入内存缓存
        self._memory_cache[key] = (value, expire_time)
        
        # 如果内存缓存超出限制，移除最早的项
        if len(self._memory_cache) > self._max_memory_items:
            oldest_key = min(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k][1]
            )
            del self._memory_cache[oldest_key]
        
        # 写入数据库缓存
        with self._get_db() as (conn, cur):
            cur.execute(
                "INSERT OR REPLACE INTO cache (key, value, expire_time) VALUES (?, ?, ?)",
                (key, json.dumps(value), expire_time)
            )
            conn.commit()
    
    def delete(self, key: str) -> None:
        """
        删除缓存项
        
        Args:
            key: 要删除的缓存键
        """
        # 从内存缓存中删除
        self._memory_cache.pop(key, None)
        
        # 从数据库缓存中删除
        with self._get_db() as (conn, cur):
            cur.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._memory_cache.clear()
        with self._get_db() as (conn, cur):
            cur.execute("DELETE FROM cache")
            conn.commit() 

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