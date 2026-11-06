"""Giới hạn số lần thử đăng nhập và đăng ký (R18), chống dò mật khẩu và spam tài khoản trên bản demo công khai.

Cửa sổ trượt lưu trong bộ nhớ tiến trình. Giả định chỉ một tiến trình backend (một worker uvicorn), giống tác vụ nền;
khởi động lại thì bộ đếm về 0. Nhiều worker hoặc nhiều máy thì cần kho dùng chung (ví dụ Redis): chưa thuộc MVP.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable

from app.core.exceptions import AppError


class AttemptLimiter:
    def __init__(self, *, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> deque[float]:
        attempts = self._attempts.get(key)
        if attempts is None:
            return deque()
        while attempts and attempts[0] <= now - self._window:
            attempts.popleft()
        if not attempts:
            del self._attempts[key]
        return attempts

    def check(self, key: str) -> None:
        """Ném 429 kèm Retry-After nếu đã hết lượt trong cửa sổ hiện tại."""
        with self._lock:
            now = self._clock()
            attempts = self._recent(key, now)
            if len(attempts) >= self._limit:
                retry_after = max(1, math.ceil(attempts[0] + self._window - now))
                raise AppError(
                    429,
                    "rate_limited",
                    f"Thử quá nhiều lần; hãy đợi khoảng {math.ceil(retry_after / 60)} phút rồi thử lại",
                    headers={"Retry-After": str(retry_after)},
                )

    def hit(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            self._recent(key, now)
            self._attempts.setdefault(key, deque()).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()
