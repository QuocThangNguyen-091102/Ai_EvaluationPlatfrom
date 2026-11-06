"""Chạy một lượt đánh giá: từng test case đi qua ĐÚNG RAG pipeline của Chat, rồi tính metric và phân loại lỗi.

Runner không truy cập database. Service truyền vào:
- `ask(question) -> RagResult`: gọi pipeline dùng chung (cùng cấu hình, cùng user, cùng phạm vi quyền như Chat);
- `on_case(outcome)`: lưu kết quả từng câu ngay khi xong (để theo dõi tiến độ và không mất kết quả nếu dừng giữa chừng).

Một câu lỗi (provider, judge, ...) chỉ làm câu đó lỗi; lượt đánh giá vẫn chạy tiếp (M6-T05).
"""

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from ai_engine.embeddings.base_embedder import EmbeddingError
from ai_engine.generation.base_llm_client import LlmError
from ai_engine.pipeline.rag_result import RagResult
from evaluation.evaluators.llm_judge import JudgeError, LlmJudge
from evaluation.metrics.retrieval.mrr import reciprocal_rank
from evaluation.metrics.retrieval.ndcg_at_k import ndcg_at_k
from evaluation.metrics.retrieval.precision_at_k import precision_at_k
from evaluation.metrics.retrieval.recall_at_k import recall_at_k
from evaluation.metrics.retrieval.relevance import Span, label_relevance

UNEXPECTED_CASE_ERROR = "Lỗi hệ thống khi chạy câu hỏi này"


@dataclass(frozen=True)
class CaseInput:
    case_id: object
    question: str
    expected_behavior: str  # "answer" | "insufficient_context"
    references: list[Span]


@dataclass(frozen=True)
class MetricValue:
    name: str
    value: float | None
    method: str  # "deterministic" | "llm_judge"
    status: str  # "computed" | "failed" | "skipped"
    k: int | None = None
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CaseOutcome:
    case_id: object
    status: str  # "ok" | "error"
    category: str
    metrics: list[MetricValue]
    result: RagResult | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class RunSummary:
    total: int
    completed: int
    failed: int
    aggregates: list[MetricValue]
    categories: dict[str, int]


class EvaluationRunner:
    def __init__(
        self,
        *,
        ask: Callable[[str], RagResult],
        k: int,
        judge: LlmJudge | None,
        on_case: Callable[[CaseOutcome], None],
        judge_unavailable_reason: str = "Chưa chọn judge cho lượt đánh giá này",
    ) -> None:
        self._ask = ask
        self._k = k
        self._judge = judge
        self._on_case = on_case
        self._judge_unavailable_reason = judge_unavailable_reason

    def run(self, cases: Sequence[CaseInput]) -> RunSummary:
        outcomes = []
        for case in cases:
            outcome = self._run_case(case)
            self._on_case(outcome)
            outcomes.append(outcome)
        return summarize(outcomes, self._k)

    def _run_case(self, case: CaseInput) -> CaseOutcome:
        try:
            result = self._ask(case.question)
        except (LlmError, EmbeddingError) as error:
            return CaseOutcome(case.case_id, "error", "error", [], error_message=str(error))
        except Exception:
            return CaseOutcome(case.case_id, "error", "error", [], error_message=UNEXPECTED_CASE_ERROR)

        metrics = [self._behavior_metric(case, result)]
        metrics += self._retrieval_metrics(case, result)
        metrics += self._generation_metrics(case, result)
        return CaseOutcome(case.case_id, "ok", categorize(case, result, metrics), metrics, result=result)

    @staticmethod
    def _behavior_metric(case: CaseInput, result: RagResult) -> MetricValue:
        expected_refusal = case.expected_behavior == "insufficient_context"
        correct = expected_refusal == result.insufficient_context
        return MetricValue(
            "behavior_correct",
            1.0 if correct else 0.0,
            "deterministic",
            "computed",
            details={"expected": case.expected_behavior, "insufficient_context": result.insufficient_context},
        )

    def _retrieval_metrics(self, case: CaseInput, result: RagResult) -> list[MetricValue]:
        if not case.references:
            return []  # câu không có đáp án: không có đoạn đúng để so, metric truy xuất không áp dụng
        spans = [Span(c.document_content_hash, c.char_start, c.char_end) for c in result.contexts]
        labels = label_relevance(spans, case.references)
        k = self._k
        relevant_ranks = [rank for rank, relevant in enumerate(labels.relevant, start=1) if relevant]
        return [
            MetricValue("precision_at_k", precision_at_k(labels, k), "deterministic", "computed", k=k, details={"relevant_ranks": relevant_ranks}),
            MetricValue("recall_at_k", recall_at_k(labels, k), "deterministic", "computed", k=k),
            MetricValue("reciprocal_rank", reciprocal_rank(labels), "deterministic", "computed"),
            MetricValue("ndcg_at_k", ndcg_at_k(labels, k), "deterministic", "computed", k=k),
        ]

    def _generation_metrics(self, case: CaseInput, result: RagResult) -> list[MetricValue]:
        if case.expected_behavior != "answer" or result.insufficient_context or result.mode != "llm":
            return []  # không có câu trả lời do LLM viết để chấm
        if self._judge is None:
            reason = {"reason": self._judge_unavailable_reason}
            return [
                MetricValue("faithfulness", None, "llm_judge", "skipped", details=reason),
                MetricValue("answer_relevancy", None, "llm_judge", "skipped", details=reason),
            ]
        contexts = [c.content for c in result.contexts]
        values = []
        for name, call in (
            ("faithfulness", lambda: self._judge.faithfulness(result.answer, contexts)),
            ("answer_relevancy", lambda: self._judge.answer_relevancy(case.question, result.answer)),
        ):
            try:
                score = call()
                status = "computed" if score.value is not None else "failed"
                details = score.details if score.value is not None else {**score.details, "reason": "Không xác định được điểm"}
                values.append(MetricValue(name, score.value, "llm_judge", status, details=details))
            except JudgeError as error:
                values.append(MetricValue(name, None, "llm_judge", "failed", details={"reason": str(error)}))
        return values


def categorize(case: CaseInput, result: RagResult, metrics: Sequence[MetricValue]) -> str:
    """Nhãn lỗi chính của câu (dùng cho phân tích lỗi). Thứ tự ưu tiên: hành vi sai trước, rồi truy xuất, rồi độ trung thực."""
    by_name = {m.name: m for m in metrics}
    if case.expected_behavior == "insufficient_context":
        return "ok" if result.insufficient_context else "hallucination"
    if result.insufficient_context:
        recall = by_name.get("recall_at_k")
        return "retrieval_miss" if recall is not None and recall.value == 0 else "false_refusal"
    recall = by_name.get("recall_at_k")
    if recall is not None and recall.value == 0:
        return "retrieval_miss"
    faithfulness = by_name.get("faithfulness")
    if faithfulness is not None and faithfulness.status == "computed" and faithfulness.value < 1.0:
        return "unsupported_claims"
    return "ok"


def summarize(outcomes: Sequence[CaseOutcome], k: int) -> RunSummary:
    values: dict[tuple[str, str, int | None], list[float]] = defaultdict(list)
    statuses: dict[tuple[str, str, int | None], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for outcome in outcomes:
        for metric in outcome.metrics:
            key = (metric.name, metric.method, metric.k)
            statuses[key][metric.status] += 1
            if metric.status == "computed" and metric.value is not None:
                values[key].append(metric.value)
    aggregates = []
    for key in sorted(statuses, key=lambda item: item[0]):
        name, method, metric_k = key
        items = values.get(key, [])
        counts = dict(statuses[key])
        public_name = "mrr" if name == "reciprocal_rank" else name
        if items:
            aggregates.append(MetricValue(public_name, sum(items) / len(items), method, "computed", k=metric_k, details={"cases": len(items), "statuses": counts}))
        else:
            # Không có giá trị nào tính được: ghi rõ là bỏ qua/thất bại, không điền số.
            status = "skipped" if set(counts) == {"skipped"} else "failed"
            aggregates.append(MetricValue(public_name, None, method, status, k=metric_k, details={"cases": 0, "statuses": counts}))
    categories: dict[str, int] = defaultdict(int)
    for outcome in outcomes:
        categories[outcome.category] += 1
    failed = sum(1 for o in outcomes if o.status == "error")
    return RunSummary(total=len(outcomes), completed=len(outcomes) - failed, failed=failed, aggregates=aggregates, categories=dict(categories))
