# Nguồn tài liệu của corpus đánh giá (M5-T03)

Trạng thái: **đã có corpus "Hệ Mặt Trời"** (chọn ngày 2026-11-06). Bản nháp 98 câu hỏi đã nhập, đang **chờ người duyệt**.

## Tiêu chí chọn tài liệu

- **Được phép dùng:** tài liệu công khai có giấy phép rõ ràng, hoặc tài liệu do chính bạn viết. Không dùng tài liệu mật hay dữ liệu cá nhân của người khác.
- **Theo yêu cầu của user (2026-11-06):** tránh nội dung nhạy cảm và văn bản thuộc quyền sở hữu của cơ quan chức năng. Vì vậy chọn chủ đề khoa học phổ thông trung tính, không dùng văn bản pháp luật.
- **Có văn bản trích được.** Không dùng PDF dạng ảnh quét, vì hệ thống chưa có OCR.
- **Cùng ngôn ngữ với câu hỏi.** Truy xuất chéo ngôn ngữ (câu hỏi tiếng Việt, tài liệu tiếng Anh) rất yếu (R21).
- **Đủ đa dạng** để viết khoảng 100 câu hỏi, có thông tin cần ghép từ nhiều đoạn.

## Corpus "Hệ Mặt Trời"

File nằm trong `evaluation/datasets/corpus/solar-system/`. Mỗi file mở đầu bằng một dòng ghi nguồn, rồi đến văn bản thuần lấy qua API chính thức của Wikipedia, không chỉnh sửa nội dung. Số phiên bản của từng bài nằm trong `sources.json`, để lấy lại đúng nội dung đã dùng.

| Tên file | Bài Wikipedia tiếng Việt | Phiên bản | Số từ |
|---|---|---|---|
| `he-mat-troi.txt` | [Hệ Mặt Trời](https://vi.wikipedia.org/wiki/H%E1%BB%87_M%E1%BA%B7t_Tr%E1%BB%9Di) | 75606175 (2026-10-02) | 6.691 |
| `sao-hoa.txt` | [Sao Hỏa](https://vi.wikipedia.org/wiki/Sao_H%E1%BB%8Fa) | 75685980 (2026-11-01) | 14.566 |
| `sao-moc.txt` | [Sao Mộc](https://vi.wikipedia.org/wiki/Sao_M%E1%BB%99c) | 75541125 (2026-09-10) | 10.400 |
| `mat-trang.txt` | [Mặt Trăng](https://vi.wikipedia.org/wiki/M%E1%BA%B7t_Tr%C4%83ng) | 75647291 (2026-10-17) | 17.645 |
| `sao-choi.txt` | [Sao chổi](https://vi.wikipedia.org/wiki/Sao_ch%E1%BB%95i) | 75000393 (2026-04-25) | 6.178 |

**Giấy phép:** nội dung các bài thuộc CC BY-SA 4.0 (tác giả là cộng đồng biên tập Wikipedia, xem lịch sử trang). Được dùng, chia sẻ và chỉnh sửa, kể cả công khai, với điều kiện ghi nguồn. Bản phái sinh từ chính văn bản này phải dùng cùng giấy phép. Giấy phép này **chỉ áp dụng cho các file trong thư mục corpus**, không áp dụng cho mã nguồn của dự án.

**Đặc điểm có ích cho đánh giá:**
- **Nhiều đoạn gần giống nhau giữa các hành tinh** (số vệ tinh, khoảng cách, thành phần), giúp đo khả năng lấy đúng đoạn.
- **Tài liệu mâu thuẫn nhau** ở 4 chỗ:
  - tuổi Hệ Mặt Trời: 4,55 và 4,568 tỷ năm;
  - số vệ tinh Sao Mộc: 95 và "ít nhất 80";
  - ngày tàu Juno đến Sao Mộc: 5/7/2016 và tháng 4/2016;
  - độ dày vỏ Sao Hỏa: 50 km và 24–72 km.

  Dataset giữ các chỗ này làm câu khó: câu trả lời tốt phải nêu cả hai số kèm nguồn.
- **Bài "Mặt Trăng" còn sót ký hiệu số trang** dạng `tr.120` từ lúc trích văn bản. Đây là nhiễu thật, nên giữ nguyên.

**Phạm vi kết luận:** điểm đo trên corpus này chỉ nói về văn bản khoa học phổ thông tiếng Việt, viết mạch lạc. Không suy ra cho tài liệu có nhiều bảng biểu, văn bản pháp lý hay văn bản scan.

## Dataset trên corpus này

`evaluation/datasets/solar_system_cases.json` có 98 câu:
- 64 câu hỏi sự kiện, 9 câu cần ghép nhiều đoạn, 5 câu tóm tắt;
- 20 câu không có đáp án (20%). Trong đó có các câu "suýt có": tài liệu nhắc tới chủ đề nhưng không có con số được hỏi.

Mọi câu không có đáp án đã được kiểm tra bằng cách tìm từ khóa trên toàn bộ corpus. Có 2 ứng viên bị loại vì tài liệu thật sự có đáp án: người đầu tiên lên Mặt Trăng, và thời điểm Juno kết thúc nhiệm vụ.

**Do AI soạn, chưa được người duyệt.** Cách nạp lại:

```bash
python scripts/import_corpus.py --email ban@example.com --password "..." \
    --documents evaluation/datasets/corpus/solar-system \
    --dataset evaluation/datasets/solar_system_cases.json --name "Hệ Mặt Trời"
```

## Tài liệu mẫu trong repo (chỉ để thử, không phải corpus thật)

| Tên file | Nguồn | Ghi chú |
|----------|-------|---------|
| `backend/tests/fixtures/vi_two_pages.pdf` | Do AI tạo bằng thư viện PDF với font Arial, nội dung giả định | 2 trang, dùng cho test và cho dataset mẫu `evaluation/datasets/sample_cases_vi_two_pages.json` |
