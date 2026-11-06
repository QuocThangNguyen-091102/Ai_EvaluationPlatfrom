# Nguồn tài liệu của corpus đánh giá (M5-T03)

Trạng thái: **mẫu, CHƯA có tài liệu thật**. Người dùng điền khi chọn tài liệu cho dataset đánh giá.

## Tiêu chí chọn tài liệu

- Bạn được phép dùng: tài liệu công khai có giấy phép rõ ràng, hoặc tài liệu do chính bạn viết. Không dùng tài liệu mật, dữ liệu cá nhân của người khác.
- Có văn bản trích được (không phải PDF dạng ảnh quét; hệ thống chưa có OCR).
- **Cùng ngôn ngữ với câu hỏi.** Lần chạy thử model cho thấy truy xuất chéo ngôn ngữ (câu hỏi tiếng Việt, tài liệu tiếng Anh) rất yếu (R21). Nếu corpus trộn ngôn ngữ thì ghi rõ và tách kết quả theo ngôn ngữ.
- Đủ đa dạng để viết khoảng 100 câu hỏi: nhiều chủ đề, có bảng, có thông tin cần ghép từ hai đoạn.

## Danh sách tài liệu

| Tên file (đúng như khi upload) | Nguồn (URL hoặc tác giả) | Giấy phép, quyền sử dụng | Ngôn ngữ | Số trang | Ghi chú |
|--------------------------------|--------------------------|--------------------------|----------|----------|---------|
| | | | | | |

## Tài liệu mẫu trong repo (chỉ để thử, không phải corpus thật)

| Tên file | Nguồn | Ghi chú |
|----------|-------|---------|
| `backend/tests/fixtures/vi_two_pages.pdf` | Do AI tạo bằng thư viện PDF với font Arial, nội dung giả định | 2 trang, dùng cho test và cho dataset mẫu `evaluation/datasets/sample_cases_vi_two_pages.json` |
