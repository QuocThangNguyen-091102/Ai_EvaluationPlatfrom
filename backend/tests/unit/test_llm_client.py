import json
import logging

import httpx
import pytest

from ai_engine.generation.base_llm_client import LlmError, LlmMessage, LlmRateLimitError, LlmTransientError
from ai_engine.generation.openai_compatible_client import OpenAICompatibleClient
from ai_engine.provider_retry import RetryPolicy, call_with_retry

MESSAGES = [LlmMessage("system", "hệ thống"), LlmMessage("user", "câu hỏi bí mật")]
API_KEY = "sk-khoa-bi-mat-khong-duoc-lo"


def _ok(text="Câu trả lời [1]", usage=None):
    body = {"choices": [{"message": {"role": "assistant", "content": text}}]}
    if usage is not False:
        body["usage"] = usage or {"prompt_tokens": 120, "completion_tokens": 30}
    return httpx.Response(200, json=body)


def _client(handler, *, api_key=API_KEY, max_attempts=3, sleeps=None):
    transport = httpx.MockTransport(handler)
    return OpenAICompatibleClient(
        base_url="https://llm.example/v1/",
        model="model-a",
        api_key=api_key,
        http_client=httpx.Client(transport=transport),
        retry_policy=RetryPolicy(max_attempts=max_attempts, base_delay_seconds=1.0),
        sleep=(sleeps.append if sleeps is not None else (lambda _s: None)),
    )


# ---------------------------------------------------------------------------------- client
def test_sends_openai_compatible_request_and_parses_answer_and_usage():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content)
        return _ok()

    result = _client(handler).generate(MESSAGES, temperature=0.2, max_tokens=256)

    assert seen["url"] == "https://llm.example/v1/chat/completions"
    assert seen["auth"] == f"Bearer {API_KEY}"
    assert seen["body"] == {
        "model": "model-a",
        "messages": [{"role": "system", "content": "hệ thống"}, {"role": "user", "content": "câu hỏi bí mật"}],
        "temperature": 0.2,
        "max_tokens": 256,
    }
    assert (result.text, result.prompt_tokens, result.completion_tokens) == ("Câu trả lời [1]", 120, 30)


def test_no_authorization_header_without_api_key():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("Authorization")
        return _ok()

    _client(handler, api_key=None).generate(MESSAGES, temperature=0)

    assert seen["auth"] is None


def test_missing_usage_gives_unknown_tokens_not_zero():
    result = _client(lambda r: _ok(usage=False)).generate(MESSAGES, temperature=0)

    assert result.prompt_tokens is None and result.completion_tokens is None


def test_rate_limit_is_retried_using_retry_after_then_succeeds():
    responses = iter([httpx.Response(429, headers={"Retry-After": "7"}), _ok()])
    sleeps = []

    result = _client(lambda r: next(responses), sleeps=sleeps).generate(MESSAGES, temperature=0)

    assert result.text == "Câu trả lời [1]"
    assert sleeps == [7.0]


def test_server_errors_are_retried_with_growing_delay_then_give_up():
    calls = []
    sleeps = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(LlmTransientError):
        _client(handler, max_attempts=3, sleeps=sleeps).generate(MESSAGES, temperature=0)

    assert len(calls) == 3
    assert sleeps == [1.0, 2.0]


def test_timeout_is_retried():
    attempts = iter([httpx.ReadTimeout("chậm"), None])

    def handler(request):
        error = next(attempts)
        if error:
            raise error
        return _ok()

    assert _client(handler).generate(MESSAGES, temperature=0).text == "Câu trả lời [1]"


def test_bad_key_is_not_retried_and_does_not_leak_the_key():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(401, json={"error": {"message": f"invalid key {API_KEY}"}})

    with pytest.raises(LlmError) as error:
        _client(handler).generate(MESSAGES, temperature=0)

    assert len(calls) == 1
    assert not isinstance(error.value, LlmTransientError)
    assert API_KEY not in str(error.value)
    assert "API key" in str(error.value)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"khong phai json"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": None}}]}),
    ],
)
def test_malformed_responses_become_llm_errors(response):
    with pytest.raises(LlmError):
        _client(lambda r: response).generate(MESSAGES, temperature=0)


def test_error_messages_never_contain_prompt_content():
    with pytest.raises(LlmError) as error:
        _client(lambda r: httpx.Response(400)).generate(MESSAGES, temperature=0)

    assert "câu hỏi bí mật" not in str(error.value)


def test_nothing_secret_is_logged(caplog):
    caplog.set_level(logging.DEBUG)

    _client(lambda r: _ok()).generate(MESSAGES, temperature=0)

    assert API_KEY not in caplog.text


# ---------------------------------------------------------------------------------- retry
class _Flaky(Exception):
    pass


def test_retry_returns_first_success():
    attempts = iter([_Flaky(), _Flaky(), "kết quả"])

    def op():
        value = next(attempts)
        if isinstance(value, Exception):
            raise value
        return value

    sleeps = []
    assert call_with_retry(op, retryable=(_Flaky,), policy=RetryPolicy(max_attempts=3), sleep=sleeps.append) == "kết quả"
    assert sleeps == [1.0, 2.0]


def test_retry_does_not_catch_other_errors():
    def op():
        raise ValueError("lỗi dữ liệu")

    with pytest.raises(ValueError):
        call_with_retry(op, retryable=(_Flaky,), sleep=lambda _s: None)


def test_retry_delay_is_capped():
    error = _Flaky()
    error.retry_after_seconds = 999
    attempts = iter([error, "ok"])

    def op():
        value = next(attempts)
        if isinstance(value, Exception):
            raise value
        return value

    sleeps = []
    call_with_retry(op, retryable=(_Flaky,), policy=RetryPolicy(max_delay_seconds=30), sleep=sleeps.append)

    assert sleeps == [30]


def test_policy_requires_at_least_one_attempt():
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)


def test_rate_limit_error_carries_retry_after():
    assert LlmRateLimitError("x", 3.0).retry_after_seconds == 3.0
