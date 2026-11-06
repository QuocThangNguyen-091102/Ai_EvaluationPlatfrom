"""LLM-as-a-Judge cho các metric chất lượng câu trả lời.

Judge trả về JSON; mọi phản hồi không đúng định dạng đều thành lỗi rõ ràng (JudgeError), KHÔNG đoán điểm.
Model và phiên bản prompt của judge được ghi vào kết quả để biết điểm do ai chấm.
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from ai_engine.generation.base_llm_client import LlmClient, LlmError
from evaluation.evaluators.judge_prompts import (
    DEFAULT_JUDGE_PROMPT_VERSION,
    faithfulness_messages,
    policy_messages,
    relevancy_messages,
)
from evaluation.metrics.generation.answer_relevancy import relevancy_score
from evaluation.metrics.generation.faithfulness import faithfulness_score

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


class JudgeError(Exception):
    """Judge không cho được điểm (lỗi provider hoặc phản hồi sai định dạng)."""


@dataclass(frozen=True)
class JudgeScore:
    value: float | None
    details: dict = field(default_factory=dict)


class LlmJudge:
    def __init__(self, client: LlmClient, prompt_version: str = DEFAULT_JUDGE_PROMPT_VERSION) -> None:
        self._client = client
        self.prompt_version = prompt_version

    @property
    def model_name(self) -> str:
        return self._client.model_name

    def faithfulness(self, answer: str, contexts: Sequence[str]) -> JudgeScore:
        data = self._ask_json(faithfulness_messages(self.prompt_version, answer, contexts))
        claims = data.get("claims")
        if not isinstance(claims, list) or not all(isinstance(c, dict) and isinstance(c.get("supported"), bool) for c in claims):
            raise JudgeError("Judge trả về danh sách khẳng định sai định dạng")
        flags = [c["supported"] for c in claims]
        return JudgeScore(
            value=faithfulness_score(flags),
            details={"claims": [{"claim": str(c.get("claim", "")), "supported": c["supported"]} for c in claims]},
        )

    def answer_relevancy(self, question: str, answer: str) -> JudgeScore:
        data = self._ask_json(relevancy_messages(self.prompt_version, question, answer))
        rating = data.get("score")
        if not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5:
            raise JudgeError("Judge trả về điểm ngoài thang 1 đến 5")
        return JudgeScore(value=relevancy_score(rating), details={"rating": rating, "reason": str(data.get("reason", ""))})

    def policy_violation(self, criterion: str, request: str, response: str) -> JudgeScore:
        """Dùng cho kiểm thử bảo mật: value = 1.0 nếu judge cho là vi phạm, 0.0 nếu không."""
        data = self._ask_json(policy_messages(self.prompt_version, criterion, request, response))
        violated = data.get("violated")
        if not isinstance(violated, bool):
            raise JudgeError("Judge không trả về trường violated dạng true/false")
        return JudgeScore(value=1.0 if violated else 0.0, details={"violated": violated, "reason": str(data.get("reason", ""))})

    def _ask_json(self, messages) -> dict:
        try:
            reply = self._client.generate(messages, temperature=0.0).text
        except LlmError as error:
            raise JudgeError(f"Judge không phản hồi được: {error}") from None
        match = _JSON_OBJECT.search(reply)
        if not match:
            raise JudgeError("Judge không trả về JSON")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise JudgeError("Judge trả về JSON không hợp lệ") from None
        if not isinstance(data, dict):
            raise JudgeError("Judge trả về JSON không phải đối tượng")
        return data
