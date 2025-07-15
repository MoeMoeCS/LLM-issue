"""测试缓存系统"""
import time
from pathlib import Path

import pytest

from cache import Cache


@pytest.fixture
def temp_cache(tmp_path):
    """创建临时缓存实例"""
    cache_path = tmp_path / "test_cache.db"
    return Cache(str(cache_path))


def test_basic_operations(temp_cache):
    """测试基本的缓存操作"""
    # 设置缓存
    temp_cache.set("test_key", "test_value")
    assert temp_cache.get("test_key") == "test_value"
    
    # 获取不存在的键
    assert temp_cache.get("non_existent") is None
    
    # 删除缓存
    temp_cache.delete("test_key")
    assert temp_cache.get("test_key") is None


def test_expiration(temp_cache):
    """测试缓存过期"""
    # 设置 1 秒过期的缓存
    temp_cache.set("short_lived", "value", expire_in=1)
    assert temp_cache.get("short_lived") == "value"
    
    # 等待过期
    time.sleep(1.1)
    assert temp_cache.get("short_lived") is None


def test_complex_values(temp_cache):
    """测试复杂数据类型的缓存"""
    data = {
        "list": [1, 2, 3],
        "dict": {"a": 1, "b": 2},
        "nested": {"x": [{"y": "z"}]},
    }
    temp_cache.set("complex", data)
    assert temp_cache.get("complex") == data


def test_memory_limit(tmp_path):
    """测试内存缓存限制"""
    cache = Cache(str(tmp_path / "limit_test.db"), max_memory_items=2)
    
    # 添加三个项，应该只有最新的两个保留在内存中
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    
    # 验证所有值都能从 SQLite 中读取
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    
    # 检查内存缓存大小
    assert len(cache._memory_cache) <= 2


def test_clear(temp_cache):
    """测试清空缓存"""
    # 添加多个缓存项
    temp_cache.set("a", 1)
    temp_cache.set("b", 2)
    temp_cache.set("c", 3)
    
    # 清空缓存
    temp_cache.clear()
    
    # 验证所有项都被删除
    assert temp_cache.get("a") is None
    assert temp_cache.get("b") is None
    assert temp_cache.get("c") is None
    
    # 验证内存缓存也被清空
    assert len(temp_cache._memory_cache) == 0


def test_persistence(tmp_path):
    """测试缓存持久化"""
    db_path = tmp_path / "persist_test.db"
    
    # 第一个缓存实例
    cache1 = Cache(str(db_path))
    cache1.set("persist", "value")
    
    # 创建新的缓存实例，应该能读取到之前的值
    cache2 = Cache(str(db_path))
    assert cache2.get("persist") == "value" 