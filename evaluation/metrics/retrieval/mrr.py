from evaluation.metrics.retrieval.relevance import RelevanceLabels


def reciprocal_rank(labels: RelevanceLabels) -> float:
    """1 / hạng của chunk liên quan đầu tiên; 0 nếu không có. MRR là trung bình giá trị này qua các test case."""
    for rank, relevant in enumerate(labels.relevant, start=1):
        if relevant:
            return 1.0 / rank
    return 0.0
