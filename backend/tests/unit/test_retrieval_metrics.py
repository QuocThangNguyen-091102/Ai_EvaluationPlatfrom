"""Mỗi giá trị kỳ vọng được tính tay trong chú thích (tiêu chí M6-T02)."""

import math

import pytest

from evaluation.metrics.retrieval.mrr import reciprocal_rank
from evaluation.metrics.retrieval.ndcg_at_k import ndcg_at_k
from evaluation.metrics.retrieval.precision_at_k import precision_at_k
from evaluation.metrics.retrieval.recall_at_k import recall_at_k
from evaluation.metrics.retrieval.relevance import Span, label_relevance

REF_A = Span("doc1", 100, 150)
REF_B = Span("doc1", 400, 420)


def _labels(*chunks, references=(REF_A, REF_B)):
    return label_relevance(list(chunks), list(references))


def test_overlap_requires_same_document_and_intersecting_ranges():
    assert Span("doc1", 140, 200).overlaps(REF_A)
    assert not Span("doc1", 150, 200).overlaps(REF_A)  # chỉ chạm biên, không chồng
    assert not Span("doc2", 100, 150).overlaps(REF_A)  # khác tài liệu
    assert Span("doc1", 0, 1000).overlaps(REF_A)  # chunk bao trọn reference


def test_hand_computed_example():
    # Hạng: 1 không liên quan, 2 phủ A, 3 phủ A lần nữa, 4 phủ B, 5 không liên quan.
    labels = _labels(
        Span("doc1", 0, 50), Span("doc1", 90, 120), Span("doc1", 130, 160), Span("doc1", 410, 500), Span("doc2", 0, 10)
    )
    assert labels.relevant == [False, True, True, True, False]

    # Precision@3 = 2/3; Precision@5 = 3/5
    assert precision_at_k(labels, 3) == pytest.approx(2 / 3)
    assert precision_at_k(labels, 5) == pytest.approx(3 / 5)
    # Recall@2 = {A}/2 = 0.5; Recall@4 = {A, B}/2 = 1.0
    assert recall_at_k(labels, 2) == 0.5
    assert recall_at_k(labels, 4) == 1.0
    # Reciprocal rank = 1/2 (chunk liên quan đầu tiên ở hạng 2)
    assert reciprocal_rank(labels) == 0.5
    # NDCG@5: gain mới ở hạng 2 (A) và hạng 4 (B); hạng 3 phủ lại A nên gain 0.
    # DCG = 1/log2(3) + 1/log2(5); IDCG (2 reference) = 1/log2(2) + 1/log2(3)
    expected = (1 / math.log2(3) + 1 / math.log2(5)) / (1 + 1 / math.log2(3))
    assert ndcg_at_k(labels, 5) == pytest.approx(expected)


def test_perfect_ranking_scores_one():
    labels = _labels(Span("doc1", 100, 150), Span("doc1", 400, 420))

    assert precision_at_k(labels, 2) == 1.0
    assert recall_at_k(labels, 2) == 1.0
    assert reciprocal_rank(labels) == 1.0
    assert ndcg_at_k(labels, 2) == pytest.approx(1.0)


def test_nothing_relevant_scores_zero():
    labels = _labels(Span("doc2", 0, 10), Span("doc1", 0, 50))

    assert (precision_at_k(labels, 2), recall_at_k(labels, 2), reciprocal_rank(labels), ndcg_at_k(labels, 2)) == (0, 0, 0, 0)


def test_precision_divides_by_k_even_when_fewer_chunks_are_returned():
    labels = _labels(Span("doc1", 100, 150))

    assert precision_at_k(labels, 5) == pytest.approx(1 / 5)


def test_ndcg_never_exceeds_one_when_many_chunks_cover_the_same_reference():
    labels = _labels(*[Span("doc1", 100 + i, 150) for i in range(5)], references=(REF_A,))

    assert ndcg_at_k(labels, 5) == pytest.approx(1.0)


def test_ndcg_rewards_finding_relevant_chunks_earlier():
    early = _labels(Span("doc1", 100, 150), Span("x", 0, 1), Span("x", 0, 1), references=(REF_A,))
    late = _labels(Span("x", 0, 1), Span("x", 0, 1), Span("doc1", 100, 150), references=(REF_A,))

    assert ndcg_at_k(early, 3) > ndcg_at_k(late, 3) > 0


def test_recall_and_ndcg_are_undefined_without_references():
    labels = _labels(Span("doc1", 0, 10), references=())

    with pytest.raises(ValueError):
        recall_at_k(labels, 3)
    with pytest.raises(ValueError):
        ndcg_at_k(labels, 3)


@pytest.mark.parametrize("metric", [precision_at_k, recall_at_k, ndcg_at_k])
def test_k_must_be_positive(metric):
    with pytest.raises(ValueError):
        metric(_labels(Span("doc1", 100, 150)), 0)
