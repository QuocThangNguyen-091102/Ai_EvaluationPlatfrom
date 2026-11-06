"""Chạy bộ test case bảo mật qua RAG pipeline dùng chung (hàm `ask` do service truyền vào).

Runner không truy cập DB: service chuẩn bị tài liệu sandbox, truyền `ask(case) -> RagResult` và `on_case` để lưu.
Một case lỗi không dừng cả lượt.
"""

import logging
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from ai_engine.generation.base_llm_client import LlmError
from ai_engine.pipeline.rag_result import RagResult
from evaluation.evaluators.llm_judge import JudgeError, LlmJudge
from security.evaluators.security_result_evaluator import check_rules
from security.test_case_loader import SecurityCase

logger = logging.getLogger(__name__)

SKIPPED_NO_LLM = "Bỏ qua: test này kiểm tra hành vi của LLM nhưng lượt chạy không dùng LLM (chế độ trích đoạn)"


@dataclass
class SecurityOutcome:
    case: SecurityCase
    status: str  # pass | fail | error | skipped
    evaluator: str  # rule | judge | none
    evidence: dict = field(default_factory=dict)
    result: RagResult | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class SecuritySummary:
    total: int
    by_status: dict[str, int]
    failed_by_severity: dict[str, int]
    by_category: dict[str, dict[str, int]]


class SecurityRunner:
    def __init__(
        self,
        *,
        ask: Callable[[SecurityCase], RagResult],
        llm_available: bool,
        protected: Sequence[str],
        secrets: Mapping[str, str],
        judge: LlmJudge | None = None,
        on_case: Callable[[SecurityOutcome], None] | None = None,
    ) -> None:
        self._ask = ask
        self._llm_available = llm_available
        self._protected = protected
        self._secrets = secrets
        self._judge = judge
        self._on_case = on_case

    def run(self, cases: Sequence[SecurityCase]) -> SecuritySummary:
        outcomes = []
        for case in cases:
            outcome = self._run_case(case)
            outcomes.append(outcome)
            if self._on_case:
                self._on_case(outcome)
        return summarize(outcomes)

    def _run_case(self, case: SecurityCase) -> SecurityOutcome:
        if case.requires_llm and not self._llm_available:
            return SecurityOutcome(case, "skipped", "none", {"reason": SKIPPED_NO_LLM})
        try:
            result = self._ask(case)
        except LlmError as error:
            return SecurityOutcome(case, "error", "none", error_message=str(error))
        except Exception:
            logger.exception("Security case failed unexpectedly: key=%s", case.key)
            return SecurityOutcome(case, "error", "none", error_message="Lỗi hệ thống khi chạy test case")

        contexts = [chunk.content for chunk in result.contexts]
        violations = check_rules(
            case,
            answer=result.answer,
            insufficient_context=result.insufficient_context,
            contexts=contexts,
            protected=self._protected,
            secrets=self._secrets,
        )
        evidence = {
            "mode": result.mode,
            "contexts_count": len(contexts),
            "insufficient_context": result.insufficient_context,
            "violations": [v.as_dict() for v in violations],
        }
        if violations:
            return SecurityOutcome(case, "fail", "rule", evidence, result)

        if case.judge_criterion is None:
            return SecurityOutcome(case, "pass", "rule", evidence, result)
        if self._judge is None or result.mode != "llm":
            evidence["judge"] = {"status": "skipped", "reason": "Không có judge hoặc câu trả lời không do LLM viết"}
            return SecurityOutcome(case, "pass", "rule", evidence, result)
        try:
            score = self._judge.policy_violation(case.judge_criterion, case.question, result.answer)
        except JudgeError as error:
            # Luật đã pass; judge lỗi thì giữ kết quả theo luật nhưng ghi rõ judge không chấm được.
            evidence["judge"] = {"status": "failed", "reason": str(error)}
            return SecurityOutcome(case, "pass", "rule", evidence, result)
        evidence["judge"] = {"status": "computed", "model": self._judge.model_name, **score.details}
        return SecurityOutcome(case, "fail" if score.details["violated"] else "pass", "judge", evidence, result)


def summarize(outcomes: Sequence[SecurityOutcome]) -> SecuritySummary:
    by_status = Counter(outcome.status for outcome in outcomes)
    failed = Counter(outcome.case.severity for outcome in outcomes if outcome.status == "fail")
    by_category: dict[str, Counter] = {}
    for outcome in outcomes:
        by_category.setdefault(outcome.case.category, Counter())[outcome.status] += 1
    return SecuritySummary(
        total=len(outcomes),
        by_status=dict(by_status),
        failed_by_severity=dict(failed),
        by_category={category: dict(counts) for category, counts in by_category.items()},
    )
