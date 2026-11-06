"""Context Recall (kiểu RAGAS): các đoạn lấy về có chứa đủ thông tin để trả lời như ĐÁP ÁN THAM CHIẾU không.

LLM judge tách đáp án tham chiếu (do người viết dataset) thành các khẳng định rồi phán định từng khẳng định có được các
đoạn lấy về hỗ trợ không. Điểm = số khẳng định được hỗ trợ / tổng khẳng định. Dùng lại đúng prompt faithfulness
(judge-strict-json), chỉ thay câu trả lời của hệ thống bằng đáp án tham chiếu.

Khác Recall@k (tất định, theo vị trí câu trích): Context Recall đo theo NỘI DUNG, nên vẫn ghi nhận khi thông tin
nằm ở đoạn khác câu trích tham chiếu. Phụ thuộc judge (xem docs/metrics_notes.md); không có khẳng định nào thì None.
"""

from collections.abc import Sequence

from evaluation.metrics.generation.faithfulness import faithfulness_score


def context_recall_score(supported_flags: Sequence[bool]) -> float | None:
    return faithfulness_score(supported_flags)
