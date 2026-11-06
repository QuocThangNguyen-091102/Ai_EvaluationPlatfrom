import json
import uuid
from decimal import Decimal

import pytest

from ai_engine.generation.base_llm_client import LlmError
from ai_engine.pipeline.rag_result import RagResult
from ai_engine.retrieval.vector_retriever import RetrievedChunk
from evaluation.evaluators.llm_judge import JudgeError, LlmJudge
from evaluation.metrics.retrieval.relevance import Span
from evaluation.runners.evaluation_runner import UNEXPECTED_CASE_ERROR, CaseInput, EvaluationRunner, categorize
from tests.fakes import ScriptedLlm


def _chunk(rank, start, end, doc="h1", content="nội dung"):
    return RetrievedChunk(rank, uuid.uuid4(), uuid.uuid4(), doc, "a.txt", None, rank - 1, start, end, content, 0.9 - rank / 10)


def _result(answer="Trả lời [1]", *, contexts=None, insufficient=False, mode="llm"):
    contexts = [_chunk(1, 100, 150)] if contexts is None else contexts
    return RagResult(answer, insufficient, contexts, [], mode, "test", "m", "rag-v1", 50, 10, 5, Decimal(0))


ANSWERABLE = CaseInput("c1", "Hạn nộp?", "answer", [Span("h1", 120, 130)])
UNANSWERABLE = CaseInput("c2", "Lương giám đốc?", "insufficient_context", [])


def _run(cases, results, judge=None, k=3):
    outcomes = []
    answers = iter(results)

    def ask(question):
        value = next(answers)
        if isinstance(value, Exception):
            raise value
        return value

    summary = EvaluationRunner(ask=ask, k=k, judge=judge, on_case=outcomes.append).run(cases)
    return summary, outcomes


def _metrics(outcome):
    return {m.name: m for m in outcome.metrics}


# ---------------------------------------------------------------------------------- retrieval + behavior
def test_answerable_case_gets_retrieval_and_behavior_metrics():
    _, [outcome] = _run([ANSWERABLE], [_result()])

    metrics = _metrics(outcome)
    assert metrics["behavior_correct"].value == 1.0
    assert metrics["precision_at_k"].value == pytest.approx(1 / 3)
    assert metrics["recall_at_k"].value == 1.0
    assert metrics["reciprocal_rank"].value == 1.0
    assert metrics["precision_at_k"].k == 3
    assert outcome.category == "ok"


def test_unanswerable_case_answered_anyway_is_a_hallucination():
    _, [outcome] = _run([UNANSWERABLE], [_result("Lương là 99 triệu [1]")])

    assert _metrics(outcome)["behavior_correct"].value == 0.0
    assert "recall_at_k" not in _metrics(outcome)  # không có đoạn đúng để so
    assert outcome.category == "hallucination"


def test_unanswerable_case_correctly_refused():
    _, [outcome] = _run([UNANSWERABLE], [_result("Không đủ thông tin", insufficient=True, contexts=[])])

    assert _metrics(outcome)["behavior_correct"].value == 1.0
    assert outcome.category == "ok"


def test_refusal_when_the_answer_was_not_even_retrieved_is_a_retrieval_miss():
    _, [outcome] = _run([ANSWERABLE], [_result("Không đủ", insufficient=True, contexts=[_chunk(1, 0, 50)])])

    assert outcome.category == "retrieval_miss"


def test_refusal_although_the_right_passage_was_retrieved_is_a_false_refusal():
    _, [outcome] = _run([ANSWERABLE], [_result("Không đủ", insufficient=True)])

    assert outcome.category == "false_refusal"


# ---------------------------------------------------------------------------------- judge
def _judge(reply):
    return LlmJudge(ScriptedLlm(reply))


def _scripted_judge(faithfulness_json, relevancy_json):
    def respond(messages):
        return faithfulness_json if "NGỮ CẢNH" in messages[1].content else relevancy_json

    return _judge(respond)


def test_judge_metrics_are_computed_from_the_judges_json():
    judge = _scripted_judge(
        json.dumps({"claims": [{"claim": "a", "supported": True}, {"claim": "b", "supported": False}]}),
        'Đây là kết quả: {"score": 4, "reason": "gần đủ"}',
    )

    _, [outcome] = _run([ANSWERABLE], [_result()], judge=judge)

    metrics = _metrics(outcome)
    assert metrics["faithfulness"].value == 0.5
    assert metrics["faithfulness"].details["claims"][1]["supported"] is False
    assert metrics["answer_relevancy"].value == 0.75
    assert outcome.category == "unsupported_claims"


@pytest.mark.parametrize(
    "faithfulness_reply",
    ["không phải json", '{"claims": "sai"}', '{"claims": [{"claim": "a", "supported": "co"}]}'],
)
def test_malformed_judge_output_fails_the_metric_without_inventing_a_score(faithfulness_reply):
    judge = _scripted_judge(faithfulness_reply, '{"score": 5}')

    _, [outcome] = _run([ANSWERABLE], [_result()], judge=judge)

    faithfulness = _metrics(outcome)["faithfulness"]
    assert (faithfulness.status, faithfulness.value) == ("failed", None)
    assert faithfulness.details["reason"]
    assert _metrics(outcome)["answer_relevancy"].value == 1.0


@pytest.mark.parametrize("reply", ['{"score": 7}', '{"score": "5"}', '{"score": true}'])
def test_relevancy_outside_the_scale_fails(reply):
    with pytest.raises(JudgeError):
        _judge(lambda m: reply).answer_relevancy("q", "a")


def test_judge_provider_error_fails_the_metric_only():
    judge = _judge(lambda m: LlmError("judge hết hạn mức"))

    _, [outcome] = _run([ANSWERABLE], [_result()], judge=judge)

    assert outcome.status == "ok"
    assert _metrics(outcome)["faithfulness"].status == "failed"


def test_no_judge_means_generation_metrics_are_skipped_not_scored():
    _, [outcome] = _run([ANSWERABLE], [_result()], judge=None)

    assert {(m.name, m.status, m.value) for m in outcome.metrics if m.method == "llm_judge"} == {
        ("faithfulness", "skipped", None),
        ("answer_relevancy", "skipped", None),
    }


def test_extractive_answers_are_not_judged():
    judge = _judge(lambda m: '{"score": 5}')

    _, [outcome] = _run([ANSWERABLE], [_result(mode="extractive")], judge=judge)

    assert not [m for m in outcome.metrics if m.method == "llm_judge"]


def test_empty_claim_list_is_unknown_not_perfect():
    judge = _scripted_judge('{"claims": []}', '{"score": 3}')

    _, [outcome] = _run([ANSWERABLE], [_result()], judge=judge)

    assert (_metrics(outcome)["faithfulness"].status, _metrics(outcome)["faithfulness"].value) == ("failed", None)


# ---------------------------------------------------------------------------------- lỗi theo câu, tổng hợp
def test_one_failing_case_does_not_stop_the_run():
    summary, outcomes = _run(
        [ANSWERABLE, ANSWERABLE, UNANSWERABLE],
        [_result(), LlmError("LLM lỗi"), _result("x", insufficient=True, contexts=[])],
    )

    assert [o.status for o in outcomes] == ["ok", "error", "ok"]
    assert outcomes[1].error_message == "LLM lỗi"
    assert (summary.total, summary.completed, summary.failed) == (3, 2, 1)
    assert summary.categories == {"ok": 2, "error": 1}


def test_unexpected_exception_is_contained_without_leaking_details():
    _, [outcome] = _run([ANSWERABLE], [RuntimeError("chi tiết nội bộ")])

    assert (outcome.status, outcome.error_message) == ("error", UNEXPECTED_CASE_ERROR)


def test_aggregates_average_only_computed_values_and_count_cases():
    summary, _ = _run(
        [ANSWERABLE, ANSWERABLE],
        [_result(), _result(contexts=[_chunk(1, 0, 50), _chunk(2, 120, 160)])],
    )

    aggregates = {m.name: m for m in summary.aggregates}
    assert aggregates["recall_at_k"].value == 1.0
    assert aggregates["mrr"].value == pytest.approx((1.0 + 0.5) / 2)
    assert aggregates["mrr"].details == {"cases": 2, "statuses": {"computed": 2}}
    # Chỉ có giá trị skipped: vẫn có dòng tổng hợp để giao diện ghi "bỏ qua", nhưng không điền số.
    assert (aggregates["faithfulness"].value, aggregates["faithfulness"].status) == (None, "skipped")
    assert aggregates["faithfulness"].details == {"cases": 0, "statuses": {"skipped": 2}}


def test_categorize_prefers_behavior_over_other_signals():
    assert categorize(UNANSWERABLE, _result(), []) == "hallucination"
