"""使用大模型为 Issue 生成一句话摘要"""
import asyncio
import hashlib
import json
import logging
import os
import re
from textwrap import shorten
from typing import List, Optional

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

from cache import Cache
from config import (
    OPENAI_BASE_URL,
    OPENAI_API_KEY,
    MODEL_NAME,
    SUMMARY_PROMPT,
)

# 设置日志
logger = logging.getLogger(__name__)

# 自定义异常类
class LLMSummaryError(Exception):
    """LLM 摘要生成相关的异常基类"""


class LLMAPIError(LLMSummaryError):
    """LLM API 调用异常"""


class LLMTimeoutError(LLMSummaryError):
    """LLM API 超时异常"""


class LLMRateLimitError(LLMSummaryError):
    """LLM API 速率限制异常"""


class LLMQualityError(LLMSummaryError):
    """摘要质量不符合要求"""


# 配置项
DEFAULT_CONCURRENCY = "10"
MAX_BATCH_SIZE = 50  # 每批处理的最大 issue 数量
CACHE_EXPIRE = 86400  # 缓存过期时间（1天）
CONCURRENCY_LIMIT = int(os.getenv("LLM_CONCURRENCY_LIMIT", DEFAULT_CONCURRENCY))

# 初始化客户端
client = AsyncOpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)

# 初始化缓存
cache = Cache(db_path=".cache/summaries.db")

# 摘要质量检查的正则表达式
SUMMARY_CHECKS = {
    "length": re.compile(r"^[「『](.{5,30})[」』]$"),  # 检查长度和引号
    "style": re.compile(r"[「『][^」』]+[」』]$"),  # 检查格式一致性
}


def _get_cache_key(issue) -> str:
    """生成 issue 的缓存键"""
    # 使用 issue 的关键信息生成缓存键
    key_data = {
        "number": issue.number,
        "title": issue.title,
        "body": issue.body,
        "updated_at": str(issue.updated_at),
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return f"summary:{hashlib.sha256(key_str.encode()).hexdigest()}"


def _check_summary_quality(summary: str) -> Optional[str]:
    """
    检查摘要质量，返回错误信息或 None
    """
    if not summary:
        return "摘要为空"
    
    if not SUMMARY_CHECKS["length"].match(summary):
        return "摘要长度不符或缺少引号"
    
    if not SUMMARY_CHECKS["style"].match(summary):
        return "摘要格式不符合要求"
    
    return None


async def _get_retry_delay(error_type: str, attempt: int) -> float:
    """根据错误类型和重试次数返回等待时间"""
    if error_type == "timeout":
        return 2 ** attempt  # 指数退避：1, 2, 4, 8...
    elif error_type == "rate_limit":
        return 5 * (attempt + 1)  # 线性增长：5, 10, 15...
    else:
        return 1  # 其他错误固定等待1秒


async def summarize_batch(
    issues: List,
    concurrency_limit: int = CONCURRENCY_LIMIT,
    force_refresh: bool = False,
) -> List[str]:
    """
    并发调用大模型，为 issues 列表生成一句话摘要
    
    Args:
        issues: Issue 对象列表
        concurrency_limit: 并发限制数量
        force_refresh: 是否强制刷新缓存
        
    Returns:
        摘要字符串列表
        
    Raises:
        LLMSummaryError: 当批处理失败时抛出
    """
    # 限制批量处理大小
    if len(issues) > MAX_BATCH_SIZE:
        logger.warning(
            "Batch size %d exceeds limit %d, splitting into multiple batches",
            len(issues), MAX_BATCH_SIZE
        )
        results = []
        for i in range(0, len(issues), MAX_BATCH_SIZE):
            batch = issues[i:i + MAX_BATCH_SIZE]
            batch_results = await summarize_batch(
                batch, concurrency_limit, force_refresh
            )
            results.extend(batch_results)
        return results

    semaphore = asyncio.Semaphore(concurrency_limit)

    async def _summarize_single_issue(issue):
        """为单个 issue 生成摘要"""
        # 检查缓存
        cache_key = _get_cache_key(issue)
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached:
                logger.debug("Cache hit for issue #%s", issue.number)
                return cached

        async with semaphore:
            prompt = SUMMARY_PROMPT.format(
                type_=issue.type_,
                priority=issue.priority,
                title=issue.title,
                body=(issue.body or "")[:1500],
            )

            # 重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    resp = await client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=40,
                        temperature=0.3,
                    )
                    summary = (resp.choices[0].message.content or "").strip()
                    
                    # 质量检查
                    quality_error = _check_summary_quality(summary)
                    if quality_error:
                        logger.warning(
                            "Quality check failed for issue #%s: %s",
                            issue.number, quality_error
                        )
                        if attempt == max_retries - 1:
                            raise LLMQualityError(quality_error)
                        continue
                    
                    logger.debug(
                        "Successfully generated summary for issue #%s", issue.number
                    )
                    
                    # 缓存结果
                    cache.set(cache_key, summary, expire_in=CACHE_EXPIRE)
                    return summary

                except (APITimeoutError, RateLimitError, APIError, Exception) as e:
                    error_type = (
                        "timeout" if isinstance(e, APITimeoutError)
                        else "rate_limit" if isinstance(e, RateLimitError)
                        else "api" if isinstance(e, APIError)
                        else "unknown"
                    )
                    
                    logger.warning(
                        "%s error for issue #%s, attempt %d/%d: %s",
                        error_type.title(), issue.number, attempt + 1, max_retries, e
                    )
                    
                    if attempt == max_retries - 1:
                        logger.error(
                            "All retries failed for issue #%s", issue.number
                        )
                        break
                    
                    delay = await _get_retry_delay(error_type, attempt)
                    await asyncio.sleep(delay)

            # 所有重试都失败，使用本地 fallback
            logger.info("Using local fallback for issue #%s", issue.number)
            raw_text = " ".join(filter(None, [issue.title, issue.body])).strip()
            summary = f"「{shorten(raw_text, 28, placeholder='…')}」"
            cache.set(cache_key, summary, expire_in=CACHE_EXPIRE)
            return summary

    try:
        results = await asyncio.gather(
            *[_summarize_single_issue(issue) for issue in issues]
        )
        logger.info("Successfully processed %d issues", len(results))
        return results
    except Exception as e:
        logger.error("Batch processing failed: %s", e)
        raise LLMSummaryError("Failed to process issue batch") from e


async def summarize_single(
    issue,
    force_refresh: bool = False,
) -> str:
    """
    为单个 issue 生成摘要的便捷函数
    
    Args:
        issue: Issue 对象
        force_refresh: 是否强制刷新缓存
        
    Returns:
        摘要字符串
    """
    results = await summarize_batch([issue], force_refresh=force_refresh)
    return results[0]
