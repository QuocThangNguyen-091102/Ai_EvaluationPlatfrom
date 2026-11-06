"""LLM client cho mọi API theo chuẩn "OpenAI-compatible" (`POST {base_url}/chat/completions`).

Nhiều provider có gói miễn phí và LLM chạy cục bộ dùng chung định dạng này, nên một adapter dùng được cho nhiều nơi;
đổi nơi chỉ là đổi `base_url`, `model` và `api_key` trong cấu hình.
"""

from collections.abc import Sequence

import httpx

from ai_engine.generation.base_llm_client import (
    LlmClient,
    LlmError,
    LlmMessage,
    LlmRateLimitError,
    LlmResult,
    LlmTransientError,
)
from ai_engine.provider_retry import RetryPolicy, call_with_retry


class OpenAICompatibleClient(LlmClient):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        provider_name: str = "openai-compatible",
        timeout_seconds: float = 60.0,
        retry_policy: RetryPolicy = RetryPolicy(),
        http_client: httpx.Client | None = None,
        sleep=None,
    ) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model = model
        self._api_key = api_key
        self._provider_name = provider_name
        self._timeout = timeout_seconds
        self._retry_policy = retry_policy
        self._http = http_client or httpx.Client()
        self._sleep = sleep

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model

    def generate(
        self, messages: Sequence[LlmMessage], *, temperature: float, max_tokens: int | None = None
    ) -> LlmResult:
        payload: dict = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        kwargs = {"retryable": (LlmTransientError,), "policy": self._retry_policy}
        if self._sleep is not None:
            kwargs["sleep"] = self._sleep
        return call_with_retry(lambda: self._send(payload), **kwargs)

    def _send(self, payload: dict) -> LlmResult:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            response = self._http.post(self._url, json=payload, headers=headers, timeout=self._timeout)
        except httpx.TimeoutException:
            raise LlmTransientError("LLM không phản hồi kịp (timeout)") from None
        except httpx.HTTPError:
            raise LlmTransientError("Không kết nối được tới LLM") from None

        status = response.status_code
        if status == 429:
            raise LlmRateLimitError("LLM từ chối vì vượt hạn mức tần suất", _retry_after(response))
        if status >= 500:
            raise LlmTransientError(f"LLM gặp lỗi phía máy chủ (HTTP {status})")
        if status in (401, 403):
            raise LlmError("LLM từ chối xác thực: kiểm tra API key và quyền truy cập model")
        if status >= 400:
            raise LlmError(f"LLM từ chối yêu cầu (HTTP {status})")

        try:
            body = response.json()
            text = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LlmError("Phản hồi của LLM không đúng định dạng") from None
        if not isinstance(text, str):
            raise LlmError("Phản hồi của LLM không có nội dung văn bản")

        usage = body.get("usage") or {}
        return LlmResult(
            text=text.strip(),
            prompt_tokens=_as_int(usage.get("prompt_tokens")),
            completion_tokens=_as_int(usage.get("completion_tokens")),
        )


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _as_int(value) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None
