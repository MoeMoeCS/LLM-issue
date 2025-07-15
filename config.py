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
TYPE_PATTERNS = TYPE_STRINGS  # 只保留字符串，不提前编译

# ---------- 优先级关键词 ----------
PRIORITY_STRINGS = {
    "P0": ["priority/critical", "critical"],
    "P1": ["priority/major", "major"],
    "P2": ["priority/minor", "minor"],
}
PRIORITY_RULES = PRIORITY_STRINGS  # 只保留字符串，不提前编译

# ---------- LLM 配置 ----------
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
SUMMARY_PROMPT = """请用一句话（不超过 30 个汉字）总结下方 GitHub Issue 的核心内容，仅返回摘要：
标题：{title}
正文：
{body}
"""