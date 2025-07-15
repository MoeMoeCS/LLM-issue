# GitHub Issue 速览器

简体中文 | [English](README.md)

一个用于抓取、筛选并自动摘要 GitHub Issue 的命令行工具，支持大模型（如 OpenAI）自动生成一句话摘要。

## 功能特点

- 支持抓取任意仓库的 open issues
- 自动过滤已分配、已关闭或无效的 issue
- 按类型和优先级自动分类
- 使用大模型（如 OpenAI GPT）为每个 issue 生成一句话摘要
- 输出 Markdown 表格和项目总览摘要
- 缓存 API 响应和摘要结果，提高性能
- 支持批量处理，自动限流
- 摘要质量控制和格式统一
- 大模型不可用时自动回退到本地摘要

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

### 3. 可选环境变量

```bash
# 缓存配置
export CACHE_DB_PATH=.cache/cache.db  # 缓存数据库位置
export CACHE_MAX_MEMORY_ITEMS=1000    # 内存缓存最大条目数
export CACHE_CLEANUP_INTERVAL=3600    # 缓存清理间隔（秒）

# 大模型配置
export LLM_CONCURRENCY_LIMIT=10       # 最大并发请求数
export OPENAI_BASE_URL=https://api.openai.com/v1  # API 端点
export MODEL_NAME=gpt-3.5-turbo       # 使用的模型
```

## 配置

- 通过 `config.py` 自定义：
  - Issue 分类关键词
  - 优先级规则和标签
  - 大模型提示词模板
  - Issue 过滤规则

## 输出格式

工具会生成：
1. 项目概览，包含 issue 统计信息
2. 详细的 Markdown 表格，包含：
   - Issue 编号和类型
   - 优先级
   - 一句话摘要
   - 关键标签
   - 创建时间
   - 直接链接

输出示例：
```markdown
# owner/repo Issues 速览

目前共有 **50** 个待解决 Issue（Bug 20 个 / 新功能 15 个），平均优先级 P1，最新更新于 2024-03-20。

| #Issue | 类型 | 优先级 | 标题 | 一句话摘要 | 关键标签 | 创建时间 | 地址 |
|--------|------|--------|------|------------|----------|----------|------|
| #123 | Bug | P1 | 登录失败 | 「登录页面在高并发时报错」 | backend, critical | 2024-03-19 | 🔗 |
```

## 依赖

- Python 3.8+
- httpx
- typer
- pydantic
- rich
- openai

## 贡献

欢迎提交 Pull Request 来改进这个项目！

## 许可证

Apache License 2.0 