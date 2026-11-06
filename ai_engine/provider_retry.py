"""Retry có giới hạn với backoff tăng dần cho lỗi tạm thời của provider mạng (LLM, judge).

Chỉ retry lỗi được khai báo là tạm thời (timeout, rate limit, lỗi 5xx). Lỗi do dữ liệu hoặc cấu hình (sai key,
request sai) phải báo ngay, retry chỉ tốn thời gian và hạn mức.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts phải ít nhất là 1")


def call_with_retry(
    operation: Callable[[], T],
    *,
    retryable: tuple[type[BaseException], ...],
    policy: RetryPolicy = RetryPolicy(),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Gọi `operation`; nếu ném lỗi thuộc `retryable` thì chờ rồi thử lại, tối đa `policy.max_attempts` lần.

    Nếu lỗi có thuộc tính `retry_after_seconds` (ví dụ từ header Retry-After) thì chờ theo đó, không vượt max_delay.
    """
    attempt = 1
    while True:
        try:
            return operation()
        except retryable as error:
            if attempt >= policy.max_attempts:
                raise
            suggested = getattr(error, "retry_after_seconds", None)
            delay = suggested if suggested is not None else policy.base_delay_seconds * (2 ** (attempt - 1))
            sleep(min(max(delay, 0.0), policy.max_delay_seconds))
            attempt += 1
