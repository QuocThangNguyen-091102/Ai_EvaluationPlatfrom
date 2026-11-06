from evaluation.metrics.retrieval.relevance import RelevanceLabels


def precision_at_k(labels: RelevanceLabels, k: int) -> float:
    """Tỷ lệ chunk liên quan trong k chunk đầu. Chia cho k (không chia cho số chunk thực có), theo định nghĩa chuẩn:
    hệ thống trả ít hơn k chunk cũng không được lợi."""
    if k < 1:
        raise ValueError("k phải ít nhất là 1")
    return sum(labels.relevant[:k]) / k
