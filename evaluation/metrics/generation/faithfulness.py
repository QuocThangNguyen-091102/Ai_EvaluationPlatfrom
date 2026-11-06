"""Faithfulness: tỷ lệ khẳng định trong câu trả lời được ngữ cảnh hỗ trợ (theo phán định của LLM judge).

Giới hạn: phụ thuộc judge tách khẳng định và phán định đúng; judge có thể thiên lệch hoặc không ổn định. Cần đối chiếu
với chấm tay một mẫu (M6-T07). Xem docs/metrics_notes.md.
"""

from collections.abc import Sequence


def faithfulness_score(supported_flags: Sequence[bool]) -> float | None:
    """None khi không có khẳng định nào (không xác định), không trả 1 hay 0 thay thế."""
    if not supported_flags:
        return None
    return sum(1 for flag in supported_flags if flag) / len(supported_flags)
