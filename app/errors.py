"""对用户可见的业务错误。视图层把它变成 JSON 或页面提示，不返回堆栈。"""

from __future__ import annotations


class BusinessError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class MoneyError(BusinessError):
    """金额无法安全地换成整数分。"""
