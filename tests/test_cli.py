import pytest
from unittest.mock import patch, AsyncMock
import sys
from typer.testing import CliRunner
import github_issue_summarizer

runner = CliRunner()

def make_issue(**kwargs):
    from github_issue_summarizer import Issue
    from datetime import datetime
    base = dict(number=1, title="Test", body="", labels=[], assignees=[], state="open", created_at=datetime.now(), updated_at=datetime.now(), html_url="")
    base.update(kwargs)
    return Issue(**base)

@patch("github_issue_summarizer.fetch_issues", new_callable=AsyncMock)
@patch("github_issue_summarizer.summarize_batch", new_callable=AsyncMock)
def test_main_cli(mock_summarize, mock_fetch):
    # 模拟 fetch_issues 返回 2 个 issue
    mock_fetch.return_value = [make_issue(title="Bug: crash"), make_issue(title="Feature: add")]
    mock_summarize.return_value = ["crash summary", "feature summary"]
    result = runner.invoke(github_issue_summarizer.app, ["owner/repo", "--token", "dummy"])
    assert result.exit_code == 0
    # 断言表格输出中包含 issue 标题
    assert "Bug: crash" in result.output
    assert "Feature: add" in result.output 