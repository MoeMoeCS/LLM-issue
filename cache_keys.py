"""缓存 key 生成与管理模块"""
import hashlib
import json
from typing import Any, Dict

from config import MODEL_NAME, SUMMARY_PROMPT

def _hash_dict(data: Dict[str, Any]) -> str:
    """将字典转换为稳定的哈希值"""
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()

def get_github_issues_key(repo: str, token: str | None) -> str:
    """生成 GitHub Issues 列表的缓存键"""
    key_data = {
        "repo": repo,
        "token_hash": hashlib.sha256(token.encode()).hexdigest() if token else "no_token",
        "type": "github_issues",
    }
    return f"github_issues:{_hash_dict(key_data)}"

def get_summary_key(
    issue_number: int,
    issue_title: str,
    issue_body: str | None,
    updated_at: str,
) -> str:
    """生成摘要的缓存键，包含模型和提示词上下文"""
    key_data = {
        "number": issue_number,
        "title": issue_title,
        "body": issue_body,
        "updated_at": updated_at,
        # 上下文信息
        "model": MODEL_NAME,
        "prompt_hash": hashlib.sha256(SUMMARY_PROMPT.encode()).hexdigest(),
    }
    return f"summary:{_hash_dict(key_data)}" 