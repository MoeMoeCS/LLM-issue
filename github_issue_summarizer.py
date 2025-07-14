#!/usr/bin/env python3
"""
GitHub Issue 速览器 CLI
支持大模型自动生成一句话摘要
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import httpx
import typer
from pydantic import BaseModel
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from config import (
    DONE_KEYWORDS,
    NOISE_LABELS,
    PRIORITY_RULES,
    PRIORITY_STRINGS,
    TYPE_PATTERNS,
)
from llm_summary import summarize_batch
from utils import setup_logger

logger = setup_logger()

# ---------- 数据模型 ----------
class Issue(BaseModel):
    """单个 GitHub Issue 的结构化信息"""

    number: int
    title: str
    body: str | None
    labels: List[str]
    assignees: List[str]
    state: str
    created_at: datetime
    updated_at: datetime
    html_url: str
    type_: str = ""
    priority: str = ""


# ---------- 正则预编译 ----------
TYPE_PATTERNS_COMPILED = {
    k: [re.compile(p, re.I) for p in lst] for k, lst in TYPE_PATTERNS.items()
}
PRIORITY_RULES_COMPILED = {
    k: [re.compile(p, re.I) for p in lst] for k, lst in PRIORITY_RULES.items()
}


# ---------- 分类与过滤 ----------
def classify_issue(issue: Issue) -> Issue:
    """根据标题和正文推断 issue 的类型与优先级"""
    text = f"{issue.title} {issue.body or ''}".lower()

    # 类型
    for issue_type, patterns in TYPE_PATTERNS_COMPILED.items():
        if any(p.search(text) for p in patterns):
            issue.type_ = issue_type
            break
    else:
        issue.type_ = "Other"

    # 优先级
    for prio, patterns in PRIORITY_RULES_COMPILED.items():
        if any(p.search(text) for p in patterns):
            issue.priority = prio
            break
        # 额外检查 label 里是否直接包含字符串
        if any(s.strip("/") in issue.labels for s in PRIORITY_STRINGS[prio]):
            issue.priority = prio
            break
    else:
        issue.priority = "P2"
    return issue


def should_include(issue: Issue) -> bool:
    """返回 True 表示保留该 issue"""
    if issue.state != "open":
        return False
    if issue.assignees:
        return False
    content = f"{issue.title} {issue.body or ''}".lower()
    if any(kw in content for kw in DONE_KEYWORDS):
        return False
    if any(lbl.lower() in map(str.lower, NOISE_LABELS) for lbl in issue.labels):
        return False
    return True


# ---------- 抓取 ----------
GITHUB_API = "https://api.github.com"
PER_PAGE = 100
MAX_ITEMS = 10_000


async def fetch_issues(repo: str, token: str | None) -> List[Issue]:
    """抓取指定仓库的 open issues，自动停于 GitHub 上限"""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    issues: List[Issue] = []
    page = 1

    async with httpx.AsyncClient(
        http2=True,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        timeout=30,
    ) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=Console(stderr=True),
        ) as progress:
            task = progress.add_task("Fetching issues...", total=None)
            while len(issues) < MAX_ITEMS:
                r = await client.get(
                    f"{GITHUB_API}/repos/{repo}/issues",
                    headers=headers,
                    params={
                        "state": "open",
                        "sort": "updated",
                        "direction": "desc",
                        "per_page": PER_PAGE,
                        "page": page,
                    },
                )

                if r.status_code == 404:
                    logger.error("Repository not found")
                    sys.exit(1)
                if r.status_code == 422:
                    logger.info("No more issues (422), stopping.")
                    break
                if r.status_code == 403:
                    logger.error("Rate limit or token error: %s", r.text)
                    sys.exit(1)
                r.raise_for_status()

                data = r.json()
                if not data:
                    break

                for item in data:
                    if "pull_request" in item:
                        continue
                    issue = Issue(
                        number=item["number"],
                        title=item["title"],
                        body=item.get("body") or "",
                        labels=[l["name"] for l in item["labels"]],
                        assignees=[a["login"] for a in item["assignees"]],
                        state=item["state"],
                        created_at=datetime.fromisoformat(
                            item["created_at"].replace("Z", "+00:00")
                        ),
                        updated_at=datetime.fromisoformat(
                            item["updated_at"].replace("Z", "+00:00")
                        ),
                        html_url=item["html_url"],
                    )
                    issue = classify_issue(issue)
                    if should_include(issue):
                        issues.append(issue)

                remain = int(r.headers.get("x-ratelimit-remaining", 1))
                reset_ts = int(r.headers.get("x-ratelimit-reset", 0))
                if remain < 10 and reset_ts:
                    wait = max(reset_ts - int(datetime.now().timestamp()), 0) + 1
                    logger.warning("Rate limit low, sleeping %ds", wait)
                    await asyncio.sleep(wait)

                page += 1
                progress.update(task, advance=PER_PAGE)

    logger.info("Fetched %d issues after filtering", len(issues))
    return issues


# ---------- 摘要 & 输出 ----------
async def build_summary_async(issues: List[Issue], repo: str) -> tuple[str, str]:
    """生成项目总览与 Markdown 表格"""
    total = len(issues)
    bugs = sum(1 for i in issues if i.type_ == "Bug")
    features = sum(1 for i in issues if i.type_ == "Feature Request")
    scores = {"P0": 0, "P1": 1, "P2": 2}
    avg_score = (
        round(sum(scores.get(i.priority, 2) for i in issues) / total) if total else 2
    )
    latest = (
        max(issues, key=lambda i: i.updated_at).updated_at.strftime("%Y-%m-%d")
        if issues
        else "N/A"
    )
    oneliner = (
        f"{repo} 目前共有 **{total}** 个待解决 Issue"
        f"（Bug {bugs} 个 / 新功能 {features} 个），"
        f"平均优先级 P{avg_score}，最新更新于 {latest}。"
    )

    summaries = await summarize_batch(issues[:100])
    md_rows = [
        "| #Issue | 类型 | 优先级 | 标题 | 一句话摘要 | 关键标签 | 创建时间 | 地址 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for issue, summary in zip(issues[:100], summaries):
        labels = ", ".join(issue.labels[:3])
        md_rows.append(
            f"| {issue.number} | {issue.type_} | {issue.priority} | {issue.title} "
            f"| {summary} | {labels} | {issue.created_at.date()} "
            f"| [🔗]({issue.html_url}) |"
        )
    return oneliner, "\n".join(md_rows)


def save_outputs(repo: str, oneliner: str, md_table: str, issues: List[Issue]) -> None:
    """保存结果到本地文件"""
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    summary = f"# {repo} Issues 速览\n\n{oneliner}\n\n{md_table}"
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    (out_dir / "filtered_issues.json").write_text(
        json.dumps(
            [i.model_dump(mode="json") for i in issues],
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    console = Console()
    table = Table(title=f"{repo} 速览（前 20）")
    for col in ["#Issue", "类型", "优先级", "标题"]:
        table.add_column(col, overflow="fold", max_width=30)
    for i in issues[:20]:
        table.add_row(str(i.number), i.type_, i.priority, i.title)
    console.print(table)


# ---------- CLI ----------
app = typer.Typer(help="GitHub Issue 速览器（支持 LLM 摘要）")


@app.command()
def main(
    repo: str = typer.Argument(..., help="owner/repo 格式"),
    token: str = typer.Option(None, envvar="GH_TOKEN", help="GitHub Token"),
) -> None:
    """主入口"""
    asyncio.run(run(repo, token))


async def run(repo: str, token: str | None) -> None:
    """异步主流程"""
    issues = await fetch_issues(repo, token)
    oneliner, md_table = await build_summary_async(issues, repo)
    save_outputs(repo, oneliner, md_table, issues)
    typer.echo("✅ 完成，结果已保存至 output/")


if __name__ == "__main__":
    app()
