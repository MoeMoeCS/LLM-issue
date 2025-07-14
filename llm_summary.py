"""使用大模型为 Issue 生成一句话摘要"""
import asyncio
import logging
import os
from textwrap import shorten
from typing import List

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

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


# 可配置的并发数量
DEFAULT_CONCURRENCY = "10"
CONCURRENCY_LIMIT = int(os.getenv("LLM_CONCURRENCY_LIMIT", DEFAULT_CONCURRENCY))

client = AsyncOpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)


async def summarize_batch(issues: List, concurrency_limit: int = CONCURRENCY_LIMIT) -> List[str]:
    """
    并发调用大模型，为 issues 列表生成一句话摘要
    失败时回退到本地 shorten

    Args:
        issues: Issue 对象列表
        concurrency_limit: 并发限制数量，默认从环境变量读取

    Returns:
        摘要字符串列表

    Raises:
        LLMSummaryError: 当所有重试都失败时抛出
    """
    semaphore = asyncio.Semaphore(concurrency_limit)

    async def _summarize_single_issue(issue):
        """为单个 issue 生成摘要"""
        async with semaphore:
            prompt = SUMMARY_PROMPT.format(
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
                    logger.debug(
                        "Successfully generated summary for issue #%s", issue.number
                    )
                    return summary

                except APITimeoutError as e:
                    logger.warning(
                        "Timeout for issue #%s, attempt %d/%d: %s",
                        issue.number,
                        attempt + 1,
                        max_retries,
                        e,
                    )
                    if attempt == max_retries - 1:
                        logger.error(
                            "All timeout retries failed for issue #%s", issue.number
                        )
                        break
                    await asyncio.sleep(2 ** attempt)  # 指数退避

                except RateLimitError as e:
                    logger.warning(
                        "Rate limit hit for issue #%s, attempt %d/%d: %s",
                        issue.number,
                        attempt + 1,
                        max_retries,
                        e,
                    )
                    if attempt == max_retries - 1:
                        logger.error(
                            "Rate limit persists for issue #%s", issue.number
                        )
                        break
                    await asyncio.sleep(5 * (attempt + 1))  # 更长的等待时间

                except APIError as e:
                    logger.warning(
                        "API error for issue #%s, attempt %d/%d: %s",
                        issue.number,
                        attempt + 1,
                        max_retries,
                        e,
                    )
                    if attempt == max_retries - 1:
                        logger.error(
                            "All API retries failed for issue #%s", issue.number
                        )
                        break
                    await asyncio.sleep(1)

                except Exception as e:  # pylint: disable=broad-except
                    logger.error(
                        "Unexpected error for issue #%s: %s", issue.number, e
                    )
                    break

            # 所有重试都失败，使用本地 fallback
            logger.info("Using local fallback for issue #%s", issue.number)
            raw_text = " ".join(filter(None, [issue.title, issue.body])).strip()
            return shorten(raw_text, 60, placeholder="…")

    try:
        results = await asyncio.gather(
            *[_summarize_single_issue(issue) for issue in issues]
        )
        logger.info("Successfully processed %d issues", len(results))
        return results
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Batch processing failed: %s", e)
        raise LLMSummaryError("Failed to process issue batch") from e


async def summarize_single(issue) -> str:
    """
    为单个 issue 生成摘要的便捷函数

    Args:
        issue: Issue 对象

    Returns:
        摘要字符串
    """
    results = await summarize_batch([issue])
    return results[0]
