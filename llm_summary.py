"""
使用大模型为 Issue 生成一句话摘要
"""
import asyncio
from textwrap import shorten
from typing import List

from openai import AsyncOpenAI, APIError, APITimeoutError

from config import (
    OPENAI_BASE_URL,
    OPENAI_API_KEY,
    MODEL_NAME,
    SUMMARY_PROMPT,
)

client = AsyncOpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)


async def summarize_batch(issues: List) -> List[str]:
    """
    并发调用大模型，为 issues 列表生成一句话摘要
    失败时回退到本地 shorten
    """
    semaphore = asyncio.Semaphore(10)

    async def _one(issue):
        async with semaphore:
            prompt = SUMMARY_PROMPT.format(
                title=issue.title,
                body=(issue.body or "")[:1500],
            )
            try:
                resp = await client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=40,
                    temperature=0.3,
                )
                return resp.choices[0].message.content.strip()
            except (APIError, APITimeoutError):  # noqa: BLE001
                raw = (issue.title + " " + (issue.body or "")).strip()
                return shorten(raw, 60, placeholder="…")

    return await asyncio.gather(*map(_one, issues))
