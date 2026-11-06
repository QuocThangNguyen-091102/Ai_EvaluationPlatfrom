"""Ghi chú độ phủ (coverage notes) của một lượt kiểm thử bảo mật: nêu rõ phần CHƯA được kiểm tra.

Báo cáo bảo mật không bao giờ kết luận "an toàn tuyệt đối"; nó chỉ nói bộ test nào đã chạy, kết quả ra sao,
và giới hạn của cách kiểm tra.
"""

from collections.abc import Sequence

from security.test_case_loader import CATEGORIES, SecurityCase

STATIC_LIMITS = (
    "Luật khớp chuỗi chỉ bắt được dạng lộ nguyên văn; model có thể lộ ở dạng dịch, diễn giải, mã hóa hoặc chia nhỏ mà luật không bắt được.",
    "Mỗi test chạy một lần; câu trả lời của LLM không tất định nên một lần pass không chứng minh luôn an toàn.",
    "Chưa kiểm tra: tấn công qua nhiều lượt hội thoại, tài liệu độc dạng PDF hoặc DOCX (chỉ dùng văn bản thuần), "
    "tấn công chi phí hoặc từ chối dịch vụ, lỗ hổng hạ tầng ngoài luồng RAG (đăng nhập, upload, mạng).",
    "Bộ test nhỏ, chạy trên tài liệu sandbox do hệ thống tạo; đây không phải đánh giá an toàn đầy đủ và không kết luận hệ thống an toàn tuyệt đối.",
)


def coverage_notes(
    selected: Sequence[SecurityCase],
    *,
    requested_categories: Sequence[str] | None,
    llm_available: bool,
    judge_used: bool,
) -> list[str]:
    notes: list[str] = []
    if requested_categories:
        missing = [c for c in CATEGORIES if c not in requested_categories]
        if missing:
            notes.append(f"Không chạy các nhóm: {', '.join(missing)} (không được chọn).")
    if not llm_available:
        needs_llm = [case.key for case in selected if case.requires_llm]
        if needs_llm:
            notes.append(
                f"{len(needs_llm)} test cần LLM bị bỏ qua vì lượt chạy không dùng LLM: {', '.join(needs_llm)}. "
                "Chỉ tầng truy xuất và kiểm soát truy cập được kiểm tra thật."
            )
    elif not judge_used:
        judged = [case.key for case in selected if case.judge_criterion]
        if judged:
            notes.append(f"Không dùng judge: các test {', '.join(judged)} chỉ được chấm bằng luật khớp chuỗi.")
    notes.extend(STATIC_LIMITS)
    return notes
