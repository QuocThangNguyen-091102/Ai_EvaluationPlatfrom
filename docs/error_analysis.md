# Phân tích lỗi (M6-T07) — MẪU, chờ người điền

> Chưa có số liệu thật. Cần một lượt đánh giá trên **dataset thật đã duyệt** (M5-T03, M5-T04). Kết quả từ dataset MẪU do AI soạn không được ghi vào đây như kết quả chất lượng.

## Thông tin lượt đánh giá

- Run ID:
- Phiên bản dataset (số câu, tỉ lệ câu không có đáp án):
- Cấu hình: LLM / embedding / top_k / prompt / chunk size, overlap:
- Judge (model, prompt version) hoặc "không dùng":
- Ngày chạy:

## Bảng phân loại

| Nhãn | Số câu | % | Ví dụ (test_case_id) |
|---|---|---|---|
| ok | | | |
| hallucination | | | |
| false_refusal | | | |
| retrieval_miss | | | |
| unsupported_claims | | | |
| error | | | |

## Đọc từng nhóm (mỗi nhóm đọc ít nhất 5 câu, hoặc tất cả nếu ít hơn)

Với mỗi câu: câu hỏi, đoạn lấy về (có đúng không), câu trả lời, nguyên nhân gốc do người đánh giá.

Nguyên nhân gốc gợi ý: tài liệu không có thông tin; chunk cắt ngang ý; embedding không bắt được từ đồng nghĩa hoặc viết tắt; câu hỏi mơ hồ; tham chiếu trong dataset sai; prompt chưa ép từ chối; judge chấm sai.

## Kiểm tra judge (nếu dùng)

- Số câu người chấm lại:
- Số câu người và judge đồng ý về faithfulness:
- Nhận xét thiên lệch:

## Kết luận và việc tiếp theo

Chỉ đề xuất thay đổi có căn cứ từ các câu đã đọc, và kiểm chứng bằng một lượt đánh giá mới trên **cùng** phiên bản dataset.
