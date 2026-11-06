from evaluation.metrics.retrieval.relevance import RelevanceLabels


def recall_at_k(labels: RelevanceLabels, k: int) -> float:
    """Tỷ lệ reference context được ít nhất một trong k chunk đầu phủ tới."""
    if k < 1:
        raise ValueError("k phải ít nhất là 1")
    if labels.reference_count == 0:
        raise ValueError("Recall không xác định khi không có reference context")
    covered = set().union(*labels.covered[:k]) if labels.covered[:k] else set()
    return len(covered) / labels.reference_count
