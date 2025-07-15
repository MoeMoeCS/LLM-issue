# GitHub Issue 速览器

一个用于抓取、筛选并自动摘要 GitHub Issue 的命令行工具，支持大模型（如 OpenAI）自动生成一句话摘要。

## 功能特点

- 支持抓取任意仓库的 open issues
- 自动过滤已分配、已关闭或无效的 issue
- 按类型和优先级自动分类
- 使用大模型（如 OpenAI GPT）为每个 issue 生成一句话摘要
- 输出 Markdown 表格和项目总览摘要

## 安装

```bash
git clone https://github.com/你的用户名/issue-summarizer.git
cd issue-summarizer
pip install -r requirements.txt
```

## 用法

### 1. 设置 GitHub Token 和 OpenAI API Key

```bash
export GH_TOKEN=你的_github_token
export OPENAI_API_KEY=你的_openai_key
```

### 2. 运行速览器

```bash
python github_issue_summarizer.py owner/repo
```

- 将 `owner/repo` 替换为目标仓库名，如 `python/cpython`

## 配置

- 可通过 `config.py` 自定义关键词、标签和大模型参数

## 依赖

- Python 3.8+
- httpx
- typer
- pydantic
- rich
- openai

## 许可证

Apache License 2.0 