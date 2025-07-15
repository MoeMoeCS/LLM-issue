"""
可热改的黑名单 / 关键词表 & 大模型配置
"""
import os
import re

# ---------- 结束关键词 ----------
DONE_KEYWORDS = {
    kw.strip()
    for kw in os.getenv(
        "DONE_KEYWORDS",
        "done,fixed,resolved,closed,completed，已解决",
    ).split(",")
}

# ---------- 噪声标签 ----------
NOISE_LABELS = {
    lbl.strip()
    for lbl in os.getenv(
        "NOISE_LABELS",
        "wontfix,invalid,duplicate,help wanted,good first issue",
    ).split(",")
}

# ---------- 类型关键词 ----------
TYPE_STRINGS = {
    "Bug": [r"\bbug\b", r"\bfix\b"],
    "Enhancement": [r"\benhancement\b", r"\bimprove\b"],
    "Feature Request": [r"\bfeat\b", r"\bfeature\b"],
    "Documentation": [r"\bdocs?\b"],
    "Performance": [r"\bperf\b", r"\bperformance\b"],
    "Security": [r"\bsecurity\b"],
    "Question": [r"\bquestion\b", r"\bhow to\b"],
}
TYPE_PATTERNS = {k: [re.compile(p, re.I) for p in lst] for k, lst in TYPE_STRINGS.items()}

# ---------- 优先级关键词 ----------
PRIORITY_STRINGS = {
    "P0": ["priority/critical", "critical"],
    "P1": ["priority/major", "major"],
    "P2": ["priority/minor", "minor"],
}
PRIORITY_RULES = {k: [re.compile(p, re.I) for p in lst] for k, lst in PRIORITY_STRINGS.items()}

# ---------- LLM 配置 ----------
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
SUMMARY_PROMPT = """你是一个专业的 GitHub Issue 分析助手。请根据以下 Issue 的信息生成一句话摘要。

要求：
1. 摘要长度控制在 30 个汉字以内
2. 保持客观准确，不要添加主观评价
3. 优先关注问题的核心诉求或关键影响
4. 使用统一的语言风格和标点符号
5. 如果是 bug，说明具体问题而不是泛泛而谈
6. 如果是功能请求，说明具体需求而不是抽象描述

Issue 类型：{type_}
Issue 优先级：{priority}
Issue 标题：{title}
Issue 正文：
{body}

以下是一些示例：
Bug 示例：
- 输入：标题："Login page crashes on Firefox"
- 摘要：「Firefox 浏览器登录页面崩溃」

功能请求示例：
- 输入：标题："Add dark mode support"
- 摘要：「添加深色主题支持」

请仅返回摘要，不要包含任何其他内容："""