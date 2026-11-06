"""Answer relevancy: mức câu trả lời giải quyết đúng câu hỏi, judge chấm 1 đến 5, quy về 0 đến 1.

Khác Ragas: Ragas sinh câu hỏi ngược từ câu trả lời rồi so embedding; ở đây judge chấm trực tiếp theo thang có mô tả.
Đơn giản và dễ kiểm tra hơn nhưng phụ thuộc trực tiếp vào judge. Xem docs/metrics_notes.md.
"""


def relevancy_score(rating: int) -> float:
    if not 1 <= rating <= 5:
        raise ValueError("Điểm judge phải từ 1 đến 5")
    return (rating - 1) / 4
