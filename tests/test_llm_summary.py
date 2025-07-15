import pytest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
import llm_summary

class DummyIssue:
    def __init__(self, title, body="", number=1):
        self.title = title
        self.body = body
        self.number = number

@pytest.mark.asyncio
async def test_summarize_batch_success():
    # mock client.chat.completions.create 返回正常摘要
    with patch.object(llm_summary, "client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="summary"))]
        ))
        issues = [DummyIssue("Test title", "Test body")]
        result = await llm_summary.summarize_batch(issues, concurrency_limit=1)
        assert result == ["summary"]

@pytest.mark.asyncio
async def test_summarize_batch_timeout_retry():
    # 模拟前两次超时，第三次成功
    class DummyTimeout(Exception): pass
    with patch.object(llm_summary, "client") as mock_client:
        side_effects = [Exception("timeout"), Exception("timeout"),
                        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])]
        mock_client.chat.completions.create = AsyncMock(side_effect=side_effects)
        issues = [DummyIssue("Timeout test")] 
        result = await llm_summary.summarize_batch(issues, concurrency_limit=1)
        assert result == ["Timeout test"]

@pytest.mark.asyncio
async def test_summarize_batch_all_fail_fallback():
    # 模拟所有重试都失败，走本地 fallback
    with patch.object(llm_summary, "client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("timeout"))
        issues = [DummyIssue("Fallback title", "Fallback body")]
        result = await llm_summary.summarize_batch(issues, concurrency_limit=1)
        # fallback 会返回截断的原始文本
        assert result[0].startswith("Fallback title") 