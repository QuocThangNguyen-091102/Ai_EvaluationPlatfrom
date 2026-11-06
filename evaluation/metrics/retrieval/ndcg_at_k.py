import math

from evaluation.metrics.retrieval.relevance import RelevanceLabels


def ndcg_at_k(labels: RelevanceLabels, k: int) -> float:
    """NDCG@k với độ liên quan nhị phân.

    Gain của chunk hạng i = 1 khi nó phủ một reference CHƯA được chunk hạng cao hơn phủ (lần đầu), ngược lại 0. Nhờ vậy
    nhiều chunk cùng phủ một reference không làm điểm vượt 1. Ideal DCG giả định min(k, số reference) chunk đầu mỗi
    chunk phủ một reference mới.
    """
    if k < 1:
        raise ValueError("k phải ít nhất là 1")
    if labels.reference_count == 0:
        raise ValueError("NDCG không xác định khi không có reference context")
    seen: set[int] = set()
    dcg = 0.0
    for rank, covered in enumerate(labels.covered[:k], start=1):
        new = covered - seen
        if new:
            dcg += 1.0 / math.log2(rank + 1)
            seen |= new
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(k, labels.reference_count) + 1))
    return dcg / ideal
