"""Context Precision (kiểu RAGAS): các đoạn ĐÚNG có được xếp lên đầu không.

Tính bằng average precision trên các hạng có đoạn đúng:
    CP = (Σ_k precision@k × rel_k) / (số đoạn đúng trong danh sách)
Đoạn đúng xác định tất định bằng chồng khoảng ký tự với tham chiếu (`relevance.py`), không cần LLM, khác bản RAGAS
gốc dùng LLM để phán định từng đoạn.

Khác Precision@k: không phạt việc lấy ít đoạn hơn k, chỉ đo THỨ TỰ. Không đo việc thiếu tham chiếu (đó là Recall@k
và Context Recall). Không có đoạn đúng nào thì bằng 0.
"""

from evaluation.metrics.retrieval.relevance import RelevanceLabels


def context_precision(labels: RelevanceLabels) -> float:
    hits = 0
    total = 0.0
    for rank, relevant in enumerate(labels.relevant, start=1):
        if relevant:
            hits += 1
            total += hits / rank
    return total / hits if hits else 0.0
