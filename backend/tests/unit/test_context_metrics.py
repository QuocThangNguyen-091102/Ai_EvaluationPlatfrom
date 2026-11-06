import uuid
from decimal import Decimal

import pytest

from ai_engine.pipeline.rag_result import RagResult
from ai_engine.retrieval.vector_retriever import RetrievedChunk
from evaluation.evaluators.llm_judge import LlmJudge
from evaluation.metrics.generation.context_precision import context_precision
from evaluation.metrics.retrieval.relevance import RelevanceLabels, Span
from evaluation.runners.evaluation_runner import CaseInput, EvaluationRunner
from tests.fakes import ScriptedLlm


def _labels(*relevant):
    return RelevanceLabels(relevant=list(relevant), covered=[frozenset({0}) if r else frozenset() for r in relevant], reference_count=1)


@pytest.mark.parametrize(
    "relevant, expected",
    [
        ((True, False, False), 1.0),  # đoạn đúng đứng đầu
        ((False, True, False), 0.5),  # đứng thứ 2: precision@2 = 1/2
        ((True, False, True), (1 / 1 + 2 / 3) / 2),  # hai đoạn đúng ở hạng 1 và 3
        ((False, False, False), 0.0),  # không có đoạn đúng
        ((), 0.0),
    ],
)
def test_context_precision_is_average_precision_over_relevant_ranks(relevant, expected):
    assert context_precision(_labels(*relevant)) == pytest.approx(expected)


def _chunk(rank, start, end, content="nội dung"):
    return RetrievedChunk(rank, uuid.uuid4(), uuid.uuid4(), "h1", "a.txt", None, rank - 1, start, end, content, 0.9)


def _result(contexts, mode="extractive"):
    return RagResult("trả lời", False, contexts, [], mode, "test", "m", "rag-v1", 5, None, None, Decimal(0))


CASE = CaseInput("c1", "Hạn nộp?", "answer", [Span("h1", 120, 130)], ground_truth="Trong vòng 30 ngày.")


def _run(case, result, judge=None):
    outcomes = []
    EvaluationRunner(ask=lambda q: result, k=3, judge=judge, on_case=outcomes.append).run([case])
    return {m.name: m for m in outcomes[0].metrics}


def test_context_recall_judges_reference_answer_against_contexts_even_in_extractive_mode():
    llm = ScriptedLlm(lambda messages: '{"claims": [{"claim": "30 ngày", "supported": true}, {"claim": "kể từ thông báo", "supported": false}]}')

    metrics = _run(CASE, _result([_chunk(1, 100, 150, "nộp trong vòng 30 ngày")]), LlmJudge(llm))

    assert metrics["context_recall"].value == 0.5
    assert metrics["context_recall"].method == "llm_judge"
    # Judge nhận ĐÁP ÁN THAM CHIẾU (không phải câu trả lời của hệ thống) và các đoạn lấy về.
    sent = llm.calls[0][1].content
    assert "Trong vòng 30 ngày." in sent and "nộp trong vòng 30 ngày" in sent
    assert metrics["context_precision"].value == 1.0


def test_context_recall_without_judge_is_skipped_not_guessed():
    metrics = _run(CASE, _result([_chunk(1, 100, 150)]))

    assert (metrics["context_recall"].status, metrics["context_recall"].value) == ("skipped", None)


def test_no_retrieved_context_means_zero_recall_without_calling_judge():
    llm = ScriptedLlm()

    metrics = _run(CASE, _result([]), LlmJudge(llm))

    assert metrics["context_recall"].value == 0.0
    assert llm.calls == []


def test_malformed_judge_reply_fails_the_metric():
    metrics = _run(CASE, _result([_chunk(1, 100, 150)]), LlmJudge(ScriptedLlm(lambda m: "không phải JSON")))

    assert (metrics["context_recall"].status, metrics["context_recall"].value) == ("failed", None)


def test_no_context_recall_for_cases_without_reference_answer():
    case = CaseInput("c2", "Lương?", "insufficient_context", [])

    assert "context_recall" not in _run(case, _result([_chunk(1, 0, 10)]))
