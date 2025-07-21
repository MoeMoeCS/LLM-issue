"""自定义异常类模块"""

class GitHubError(Exception):
    """GitHub API 相关异常基类"""
    pass

class RateLimitError(GitHubError):
    """API 速率限制异常"""
    def __init__(self, reset_time: int, message: str = None):
        self.reset_time = reset_time
        self.message = message or f"Rate limit exceeded, reset at {reset_time}"
        super().__init__(self.message)

class RepoNotFoundError(GitHubError):
    """仓库不存在异常"""
    pass

class TokenError(GitHubError):
    """Token 无效或权限不足异常"""
    pass

class NetworkError(GitHubError):
    """网络请求异常"""
    pass 