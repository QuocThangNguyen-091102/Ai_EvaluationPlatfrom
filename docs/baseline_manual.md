# Baseline thủ công (M4-T08)

Trạng thái: **mẫu, CHƯA có kết quả**. Bảng dưới phải do người điền bằng kết quả hỏi đáp thật; không được điền số ước đoán.

## Mục đích

Có một điểm tham chiếu ban đầu, do con người chấm, trước khi có bộ đánh giá tự động (M6). Sau này so điểm tự động với
bảng này để biết metric có phản ánh đúng cảm nhận của người không.

## Cách làm

1. Chọn 1 đến 3 tài liệu thật bạn được phép dùng (ghi nguồn ở mục "Tài liệu" bên dưới), upload qua trang Tài liệu, chờ trạng thái "Sẵn sàng".
2. Viết khoảng 20 câu hỏi, gồm: câu có đáp án rõ trong tài liệu, câu cần ghép 2 đoạn, và **ít nhất 3 câu không có đáp án** trong tài liệu.
3. Hỏi từng câu ở trang Hỏi đáp với cùng một cấu hình (ghi tên cấu hình bên dưới). Không đổi cấu hình giữa chừng.
4. Chấm từng câu theo cột bên dưới. Chấm theo tài liệu, không theo hiểu biết riêng.
5. Tính tổng ở mục "Kết quả" từ chính bảng này.

## Bối cảnh lần chạy (điền khi chạy)

| Trường | Giá trị |
|--------|---------|
| Ngày chạy | |
| Người chấm | |
| Cấu hình (tên, LLM provider/model hoặc "extractive", Top-K, prompt) | |
| Embedding model | intfloat/multilingual-e5-small |
| Chunk size / overlap (từ) | 250 / 50 (mặc định) |

## Tài liệu

| Tên file | Nguồn | Quyền sử dụng |
|----------|-------|---------------|
| | | |

## Bảng chấm

Cột "Truy xuất đúng": đoạn chứa đáp án có nằm trong "Các đoạn đã tham khảo" không (Có/Không/Không áp dụng).
Cột "Trả lời": Đúng / Sai / Thiếu / Từ chối đúng (câu không có đáp án và hệ thống nói không đủ thông tin) / Bịa (câu không có đáp án nhưng hệ thống vẫn trả lời).

| # | Câu hỏi | Loại (dễ, ghép, không có đáp án) | Đáp án đúng theo tài liệu | Truy xuất đúng | Trả lời | Ghi chú |
|---|---------|------------------------------------|----------------------------|----------------|---------|---------|
| 1 | | | | | | |

## Kết quả (tính từ bảng, không ước đoán)

| Chỉ số | Giá trị |
|--------|---------|
| Số câu | |
| Truy xuất đúng / số câu có đáp án | |
| Trả lời đúng / số câu có đáp án | |
| Từ chối đúng / số câu không có đáp án | |
| Số câu bịa | |
