"""
pytest 单元测试：过滤与分类逻辑
"""
from datetime import datetime
import pytest  # noqa: F401  用于 pytest 自动发现用例
from github_issue_summarizer import should_include, classify_issue, Issue


def make_issue(**overrides):
    """
    快速创建 Issue 对象的测试辅助函数
    """
    base = {
        "number": 1,
        "title": "",
        "body": "",
        "labels": [],
        "assignees": [],
        "state": "open",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "html_url": "",
    }
    base.update(overrides)
    return Issue(**base)


def test_done_keyword():
    """标题或正文含有 done 关键词时应被过滤掉"""
    issue = make_issue(title="fixed bug")
    assert not should_include(issue)


def test_assignee():
    """已有人认领的 issue 应该被过滤"""
    issue = make_issue(assignees=["user"])
    assert not should_include(issue)


def test_noise_label():
    """含黑名单标签的 issue 应该被过滤"""
    issue = make_issue(labels=["wontfix"])
    assert not should_include(issue)


def test_classify_bug():
    """标题中出现 'Bug' 时应被正确分类"""
    issue = make_issue(title="Bug in parser")
    assert classify_issue(issue).type_ == "Bug"


def test_classify_priority():
    """带 priority/critical 标签时应推断为 P0"""
    issue = make_issue(labels=["priority/critical"])
    assert classify_issue(issue).priority == "P0"
