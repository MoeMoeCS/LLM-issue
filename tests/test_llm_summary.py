import asyncio
from datetime import datetime
from unittest.mock import patch
import pytest

from llm_summary import summarize_batch, LLMQualityError
from github_issue_summarizer import Issue

class DummyResp:
    class Choice:
        def __init__(self, content):
            self.message = type('msg', (), {'content': content})
    def __init__(self, content):
        self.choices = [self.Choice(content)]

@pytest.mark.asyncio
async def test_summarize_batch_cache(monkeypatch):
    # 模拟缓存命中
    issue = Issue(
        number=1,
        title="Bug: test cache",
        body="body",
        labels=[],
        assignees=[],
        state="open",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        html_url="",
    )
    # 强制缓存命中
    with patch("llm_summary.cache.get", return_value="「缓存摘要」"):
        result = await summarize_batch([issue])
        assert result == ["「缓存摘要」"]

@pytest.mark.asyncio
async def test_summarize_batch_fallback(monkeypatch):
    # 模拟 LLM 失败，触发 fallback
    issue = Issue(
        number=2,
        title="Feature: fallback",
        body="body",
        labels=[],
        assignees=[],
        state="open",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        html_url="",
    )
    # LLM 总是抛异常
    async def raise_exc(*a, **kw):
        raise Exception("fail")
    with patch("llm_summary.cache.get", return_value=None), \
         patch("llm_summary.client.chat.completions.create", raise_exc):
        result = await summarize_batch([issue])
        assert result[0].startswith("「Feature: fallback body")

@pytest.mark.asyncio
async def test_summarize_batch_quality(monkeypatch):
    # 模拟 LLM 返回不合格摘要，最终 fallback
    issue = Issue(
        number=3,
        title="Bug: quality",
        body="body",
        labels=[],
        assignees=[],
        state="open",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        html_url="",
    )
    # LLM 总是返回不合格摘要
    async def bad_summary(*a, **kw):
        return DummyResp("not valid")
    with patch("llm_summary.cache.get", return_value=None), \
         patch("llm_summary.client.chat.completions.create", bad_summary):
        result = await summarize_batch([issue], force_refresh=True)
        assert result[0].startswith("「Bug: quality body") 