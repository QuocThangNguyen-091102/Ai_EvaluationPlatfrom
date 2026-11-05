# 03. Định nghĩa MVP thực tế (M1-T03)

Trạng thái: bản nháp chờ duyệt. Mã FR, NFR tham chiếu `02_requirements.md`.

## 1. MVP xong thì demo được gì?

Một kịch bản demo 5 đến 10 phút:

1. Đăng nhập, upload vài tài liệu thật (PDF, DOCX, TXT), thấy trạng thái xử lý chuyển sang ready.
2. Hỏi trong Chat, nhận câu trả lời kèm trích dẫn; hỏi một câu không có đáp án trong tài liệu và thấy hệ thống nói không đủ thông tin.
3. Mở một dataset version đã duyệt (khoảng 100 case), chạy evaluation, xem điểm retrieval và generation, mở từng case lỗi.
4. Chạy bộ test bảo mật, xem pass/fail, severity, evidence và khuyến nghị.
5. Chạy benchmark so sánh hai cấu hình, xem chất lượng, độ trễ, chi phí, tải CSV.
6. Mọi con số trong demo đến từ run thật, đi kèm giới hạn đã biết.

## 2. Must-have (có trong MVP)

| Nhóm | Tính năng | Yêu cầu liên quan |
|------|-----------|-------------------|
| Tài khoản | Đăng ký, đăng nhập (JWT), cô lập dữ liệu theo user | FR-01, FR-02, NFR-03 |
| Ingestion | Upload PDF/DOCX/TXT, parse, chunk, embed, lưu vector, trạng thái, xóa, reprocess | FR-03 đến FR-06 |
| RAG và Chat | Hỏi đáp có trích dẫn, retrieval có phân quyền, xử lý không đủ bằng chứng, log latency/token/chi phí | FR-07 đến FR-11 |
| Dataset | Dataset, version, test case, import, duyệt và đóng băng version | FR-12 đến FR-14 |
| Evaluation | Runner, 4 retrieval metric, 2 generation metric (Faithfulness, Answer Relevancy), lưu kết quả, phân tích lỗi | FR-15 đến FR-18 |
| Security | 5 nhóm test case, runner, severity, evidence, báo cáo | FR-19 đến FR-21 |
| Benchmark | So sánh ít nhất 2 cấu hình, lịch sử run, xuất CSV | FR-22, FR-23 |
| Giao diện | Các trang Dashboard, Documents, Chat, Datasets, Evaluations, Security, Benchmarks ở mức dùng được | FR-25 |
| Hạ tầng | Docker Compose chạy db, backend, frontend; health check; migration | NFR-12 |
| Chất lượng | Unit, integration, E2E test cho luồng chính | NFR-11 |

## 3. Deferred (hoãn, làm sau MVP nếu còn thời gian)

Thứ tự cắt khi trễ tiến độ, theo danh sách task: giao diện nâng cao, xuất PDF, nhiều LLM provider, LlamaIndex.

| Tính năng | Lý do hoãn |
|-----------|------------|
| Xuất báo cáo PDF (FR-24) | CSV đã đủ để phân tích; PDF thuần trình bày |
| Context Precision và Context Recall (FR-17b) | Làm sau khi Faithfulness và Answer Relevancy đã được đối chiếu với chấm tay; thiết kế vẫn chừa chỗ (file đã có trong repo) |
| Benchmark thay chunk size hoặc embedding model (cần chunk và embed lại tài liệu; xem `07_database.md` mục 9.2). Benchmark MVP chỉ đổi LLM, Top-K, prompt, nên báo cáo không kết luận về chunking | Cần khái niệm nhiều bộ chunk song song, phức tạp chưa chứng minh được là cần |
| Nhiều LLM và embedding provider | Bắt đầu một provider, thiết kế adapter để thêm sau; benchmark vẫn so sánh được nhiều model của cùng provider |
| LlamaIndex | Bắt đầu Python-native để hiểu cơ chế; chỉ dùng nếu có lý do rõ |
| Giao diện nâng cao (biểu đồ phức tạp, lọc nhiều chiều) | Biểu đồ cơ bản đủ cho MVP |
| Chạy nền bằng hệ thống hàng đợi riêng | Không thêm hạ tầng khi chưa chứng minh nhu cầu |
| Phân quyền theo vai trò (admin, reviewer) | MVP chỉ cần cô lập theo user |
| Chia sẻ tài liệu hoặc dataset giữa các user | Làm phức tạp mô hình phân quyền |

## 4. Out-of-scope (không làm)

- Microservices, Kubernetes, Kafka, Redis, Celery khi chưa có nhu cầu được chứng minh.
- Kiểm thử bảo mật trên hệ thống không thuộc quyền kiểm soát của bạn.
- Tuyên bố ứng dụng "an toàn tuyệt đối".
- OCR cho PDF dạng ảnh quét.
- Fine-tune hoặc huấn luyện model.
- Streaming câu trả lời theo thời gian thực.
- Đa tenant, tổ chức, thanh toán.
- Đặt ngưỡng đạt/không đạt cho metric khi chưa có baseline.

## 5. Workflow chính của MVP

```
Đăng nhập -> Upload tài liệu -> Xử lý (parse, chunk, embed) -> Chat có trích dẫn
   -> Tạo dataset và duyệt version -> Chạy Evaluation (baseline)
   -> Chạy Security Testing -> Chạy Benchmark 2+ cấu hình -> Xem lịch sử, xuất CSV
```

## 6. Acceptance criteria của MVP

MVP đạt khi toàn bộ điều kiện sau đúng:

1. Máy sạch clone repo, điền `.env`, chạy `docker compose up` theo README và dùng được toàn bộ luồng ở mục 5.
2. Test cô lập quyền xanh: user A không nhận được chunk hay document của user B.
3. Có ít nhất một dataset version đã duyệt, đóng băng, khoảng 100 case, có câu hỏi không có đáp án trong tài liệu.
4. Có một run baseline đầy đủ metadata; chạy lại với cùng cấu hình cho ra metadata giống nhau.
5. Bộ test bảo mật chạy được, kết quả lưu lại và lặp lại được; báo cáo nêu phần chưa kiểm tra.
6. Có benchmark thật so sánh ít nhất 2 cấu hình, kết luận dựa trên số đo thật.
7. Chỉ có một RAG pipeline được Chat, Evaluation, Benchmark, Security cùng dùng.
8. Không có secret trong code hay Git history.
9. Unit, integration, E2E test của luồng chính chạy xanh.
10. README và tài liệu khớp với code thực tế; giới hạn đã biết được ghi rõ.
