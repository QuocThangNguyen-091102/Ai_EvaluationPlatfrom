# Kịch bản demo (khoảng 15 phút)

Chạy được hoàn toàn **không cần LLM** (chế độ trích đoạn). Phần đánh dấu **[LLM]** chỉ làm được khi đã cấu hình LLM.

## Chuẩn bị

- `docker compose up --build`, chờ 3 service healthy.
- File mẫu:
  - `backend/tests/fixtures/vi_two_pages.pdf`;
  - `evaluation/datasets/sample_cases_vi_two_pages.json`. Đây là dataset MẪU do AI soạn, **chỉ để minh họa luồng**; nói rõ điều này khi demo.

## 1. Tài liệu (2 phút)

1. Mở http://localhost:5173, đăng ký tài khoản.
2. Kéo thả `vi_two_pages.pdf` vào trang **Tài liệu**. Trạng thái chuyển từ "Đang xử lý" sang "Sẵn sàng" và tự làm mới.
3. Điểm cần nói:
   - xử lý chạy nền;
   - upload trùng nội dung bị chặn;
   - file được kiểm tra theo nội dung, không theo đuôi;
   - mỗi user chỉ thấy tài liệu của mình.

## 2. Hỏi đáp (2 phút)

1. Trang **Hỏi đáp**, hỏi: "Hồ sơ xin cấp giấy phép phải nộp trong thời hạn bao lâu?". Câu trả lời có "30 ngày", kèm nguồn và trang.
2. Mở "Nguồn", chỉ đoạn được lấy về và điểm tương đồng.
3. Điểm cần nói: chưa có LLM nên đây là chế độ trích đoạn. Khi có LLM, hệ thống viết câu trả lời có trích dẫn [1][2] và từ chối khi tài liệu không đủ thông tin. **[LLM]**

## 3. Dataset (2 phút)

1. Trang **Dataset**: tạo dataset → "Nhập từ file CSV hoặc JSON" → chọn file mẫu.
2. Mở một câu, chỉ câu trích tham chiếu đã được định vị chính xác trong tài liệu.
3. "Duyệt và đóng băng". Điểm cần nói: chỉ phiên bản đã duyệt mới đánh giá được, để kết quả tái lập được.

## 4. Đánh giá (3 phút)

1. Trang **Đánh giá**: chọn phiên bản vừa duyệt → "Chạy đánh giá". Thanh tiến độ tự cập nhật.
2. Xem metric trung bình và giải thích nhanh Recall, MRR, NDCG (rê chuột vào tên metric để đọc giải thích).
3. Bấm nhóm lỗi **"Bịa"**. Hai câu không có đáp án bị xếp loại này vì chế độ trích đoạn không biết từ chối. Đây là phát hiện đúng của hệ thống, không phải lỗi metric.
4. Mở chi tiết một câu: câu trả lời, đáp án tham chiếu, đoạn lấy về đánh dấu đúng hoặc sai.
5. "Tải báo cáo CSV" và mở bằng Excel (có BOM nên hiển thị đúng tiếng Việt).

## 5. Bảo mật (3 phút)

1. Trang **Bảo mật** → "Chạy kiểm thử" (cả 5 nhóm).
2. Kết quả khi không có LLM: 3 đạt, 9 bỏ qua.
   - AC-01, AC-02: không lấy được tài liệu của user khác, kể cả khi chỉ định thẳng ID tài liệu.
   - DL-02: secret của máy chủ không lọt ra.
3. Mở AC-01: các đoạn lấy về chỉ là tài liệu của "kẻ tấn công".
4. Đọc phần **"Giới hạn của lượt này"**. Điểm cần nói: báo cáo luôn nêu phần chưa kiểm tra và không kết luận "an toàn tuyệt đối". Có LLM thì 9 test injection và jailbreak chạy thật. **[LLM]**
5. Điểm kỹ thuật: mỗi lượt chạy trong sandbox riêng (2 user tạm), tài liệu thật không bị đụng tới, xong thì xóa.

## 6. Benchmark (2 phút)

1. Trang **Benchmark**:
   - Tên: "So sánh top_k".
   - Chọn dataset và cấu hình gốc "Mặc định".
   - Biến: top_k; giá trị: `1, 3, 5`.
2. Khi xong, xem bảng: Recall giữ 1,0 còn Precision giảm từ 1,0 xuống 0,2. Điểm cần nói: Precision@k chia cho k, mỗi câu chỉ có một đoạn đúng. Phải đọc nhiều metric cùng nhau, không chọn cấu hình theo một con số.
3. Bảng độ trễ p50 và p95, token, chi phí (0 vì không gọi LLM).

## 7. Dashboard (1 phút)

Số liệu tổng quan 6 khu vực, tóm tắt lượt kiểm thử bảo mật gần nhất, bảng so sánh các lượt đánh giá theo phiên bản dataset.

## Câu hỏi hay gặp

- *"Điểm này tốt hay xấu?"*: Chưa có baseline trên dataset thật nên hệ thống cố ý không tô màu đạt hoặc không đạt.
- *"Có an toàn không?"*: Bộ test này pass. Đó không phải là bằng chứng an toàn tuyệt đối; xem `docs/security_testing.md` mục 6.
