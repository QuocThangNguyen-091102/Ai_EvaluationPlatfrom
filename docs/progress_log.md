# Progress Log

Ghi lại kết quả sau mỗi task. Mỗi task một mục, mới nhất ở trên cùng.
Mã task theo danh sách task: `M<milestone>-T<số>` (ví dụ M1-T01).

## Mẫu một mục

```
### M?-T?? | Tên task | YYYY-MM-DD
- Trạng thái: Hoàn thành / Đang làm / Cần sửa lại
- Đã làm gì:
- File tạo/sửa:
- Đã kiểm tra thế nào (lệnh, kết quả thật):
- Lỗi gặp phải:
- Học được gì:
- Việc tiếp theo (chờ user duyệt):
```

---

### M1-T11 | GATE M1: rà soát và duyệt thiết kế | 2026-11-05
- Trạng thái: Hoàn thành. Số mâu thuẫn còn lại theo kết quả rà soát: 0 trong các mục đã xác nhận.
- Cách làm: một agent độc lập đọc lại `docs/01` đến `docs/10` và `CLAUDE.md` rồi báo 26 mục (2 HIGH, 9 MEDIUM, 15 LOW). Mình đối chiếu lại các mục chính với văn bản thật trước khi sửa. Mình cũng tự kiểm tra đường dẫn trong manifest với cây thư mục thật.
- Đã sửa (các mục chính):
  - Runner (`evaluation`, `security`) không gọi Repository; Service truyền callback lưu kết quả. Sửa 04, 05, 09.
  - MVP làm 2 generation metric (Faithfulness, Answer Relevancy); Context Precision và Context Recall là Deferred (FR-17b). Sửa 02, 03.
  - Benchmark MVP chỉ đổi `llm_model`, `top_k`, `prompt_version`; API trả 422 với giá trị khác. Sửa 02, 04, 06, 07, 08.
  - Báo cáo CSV sinh tức thì, không lưu file; bảng `reports` chỉ là lịch sử xuất. Sửa 04, 07, 08, 09.
  - Điều kiện vào M3-T01: gọi thử provider để chốt embedding model và số chiều vector. Sửa 01, 06, 10.
  - Ngoại lệ có chủ đích cho `vector_retriever.py` và `/health`. Sửa 04, 09, 10.
  - `POST /chat/messages`, trạng thái ban đầu `pending`, HTTP thay cho HTTPS ở MVP, tên tham số lệch giữa 05 và 08, chữ "đề xuất" lỗi thời.
  - Bổ sung: bảng cascade, enum status cho security và benchmark run, endpoint của Dashboard và Security page, các file docs Planned, file Alembic, R9 mở rộng cho security và benchmark run.
- Chưa sửa: mục 21 phần "package marker" chỉ ghi chú trong manifest (thêm `__init__.py` khi tạo file đầu tiên); mục 12 về hành vi RESTRICT của PostgreSQL là suy luận chưa thử, sẽ kiểm chứng khi viết migration.
- Lưu ý gate: danh sách task yêu cầu user xác nhận "được phép bắt đầu code". Mình coi yêu cầu "Tiếp tục 10 task" của user là xác nhận cho các task M2.

---

### M1-T10 | Chiến lược test, rủi ro, lộ trình học | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/10_test_risk_learning.md`
- Nội dung: 3 tầng test và bảng test theo module, chiến lược tích hợp, rủi ro kỹ thuật R9 đến R17, lộ trình học M1 đến M9, gate đo được cho M2 đến M9. Không có ngưỡng điểm tự đặt.

### M1-T09 | Cây thư mục repo + File manifest | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/09_repo_manifest.md`
- Đã xóa 4 file rỗng đầu cơ (`base_chunker.py`, `recursive_chunker.py`, `configs/app.yaml`, `scripts/init_db.sh`) và thư mục `docs/diagrams/` (9 file `.mmd` rỗng, sơ đồ nằm trong các tài liệu md).
- Đã thêm vào manifest 14 file Planned (chưa tạo): ví dụ `model_configs.py`, `retrieved_context.py`, `file_storage.py`, `rag_config.py`, `rag_result.py`, `provider_retry.py`.
- Có bảng manifest đủ cột (trách nhiệm, phụ thuộc, dùng bởi, input, output, trạng thái, milestone) và quy tắc phụ thuộc giữa thư mục.

### M1-T08 | Đặc tả API | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/08_api_contracts.md`
- Nội dung: quy ước chung, định dạng lỗi thống nhất, luồng Router tới Response, 8 nhóm endpoint (thêm nhóm `/model-configurations` ngoài danh sách Master Prompt), ánh xạ trang giao diện tới endpoint.

### M1-T07 | Thiết kế Database + ER diagram | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/07_database.md`
- Nội dung: đúng 18 entity của Master Prompt, ERD Mermaid, cách vector gắn với chunk, quy tắc cô lập user, bảng cascade, 3 điểm cần quyết định (denormalize `user_id` ở chunk, benchmark đổi chunking, bất biến version).
- Kiểm tra: chưa render Mermaid.

### M1-T06 | Deployment diagram + rà soát Technology Stack | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt (đã chọn A1, đổi được trước M3-T01)
- File: `docs/06_deployment_tech.md`
- Nội dung: Deployment diagram, bảng service, volume, biến môi trường; bảng công nghệ gắn nhãn Essential, Optional, Unnecessary; 3 phương án provider (đã chọn A1); quyết định B (Ragas và DeepEval) hoãn tới M6-T04.
- Kiểm tra: chưa render Mermaid. Tên model, giá, phiên bản thư viện chưa được xác minh, sẽ xác minh khi cài.

---

### M1-T05 | Sơ đồ Sequence (4 luồng) | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/05_sequences.md`
- Nội dung: 4 sequence diagram (Ingestion, RAG, Evaluation, Security), bảng điểm tái sử dụng RAG Pipeline, hành vi retry, lỗi, upload trùng, xóa, reprocess, bảng đối chiếu mục 5.1 đến 5.4.
- Kiểm tra: chưa render Mermaid (chưa có công cụ render trong môi trường), mới tự đọc lại cú pháp. Cần xem thử trên preview Markdown của VS Code.
- Điểm mở: quy tắc cascade khi xóa document còn chốt ở M1-T07; cơ chế xử lý run bị kẹt khi backend khởi động lại chốt ở M3 và M6.

### M1-T04 | Kiến trúc tổng thể + 3 sơ đồ đầu | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/04_architecture.md`
- Nội dung: System Context, Container, Component (Mermaid flowchart); bảng module logic và đơn vị triển khai; bảng mô tả đủ 7 module theo 8 mục (responsibility, vị trí, input/output, dependency, caller/callee, storage, failure handling, tests); 3 quyết định đã chọn kèm lý do (chạy nền, file storage, user chạy evaluation/security).
- Kiểm tra: chưa render Mermaid, xem như trên.

### M1-T03 | Định nghĩa MVP thực tế | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/03_mvp_scope.md`
- Nội dung: câu trả lời "MVP xong thì demo được gì", Must-have, Deferred, Out-of-scope, workflow chính, 10 acceptance criteria.

### M1-T02 | Người dùng mục tiêu và yêu cầu | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/02_requirements.md`
- Nội dung: 4 persona, 25 FR (FR-01 đến FR-25), 14 NFR (NFR-01 đến NFR-14), mỗi yêu cầu có cách kiểm chứng. NFR hiệu năng và chi phí chưa có số vì chưa có baseline.

### M1-T01 | Đánh giá tính khả thi và giá trị portfolio | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/01_feasibility.md`
- Nội dung: kết luận nên làm có điều kiện, giá trị, độ phức tạp theo phần, 8 rủi ro (R1 đến R8) kèm cách giảm thiểu, các điều chưa biết.

---

### NAMING | Áp dụng quy ước đặt tên | 2026-11-05
- Trạng thái: Hoàn thành
- Đã làm gì: thêm mục 8 "Quy ước đặt tên" vào `CLAUDE.md`; đổi tên các file vi phạm quy ước.
- Đổi tên: `scripts/seed_demo_data.py` → `seed_demo.py`; `docs/SESSION_NOTES.md` → `session_notes.md`; 10 file trong `docs/` đổi theo tên của danh sách task M1 (ví dụ `06_file_manifest.md` → `09_repo_manifest.md`).
- Xóa: `frontend/src/utils/` (tên chung chung, thư mục rỗng); `docs/08_learning_roadmap.md` và `docs/10_risks_and_decisions.md` (gộp vào `10_test_risk_learning.md`).
- Thêm: `docs/03_mvp_scope.md` (file rỗng, có trong danh sách task M1).
- Đã kiểm tra thế nào: `ls` thư mục `docs/`, `scripts/`, `frontend/src/`; `grep` các đường dẫn cũ trong `CLAUDE.md` và `docs/`.

---

### SETUP | Chuẩn bị môi trường làm việc | 2026-11-05
- Trạng thái: Hoàn thành
- Đã làm gì: tạo bộ khung repo `ai-evaluation-platform/` (173 file rỗng, 52 thư mục), tạo `CLAUDE.md` chứa các ràng buộc dự án, tạo `docs/session_notes.md` và file log này.
- File tạo/sửa: `CLAUDE.md`, `docs/session_notes.md`, `docs/progress_log.md`, các file rỗng theo cây thư mục.
- Đã kiểm tra thế nào: liệt kê thư mục bằng `ls`/`find` để xác nhận file tồn tại. Chưa có code nên chưa có test.
- Lỗi gặp phải: không có.
- Học được gì: không có.
- Việc tiếp theo: chờ user giao task đầu tiên (dự kiến M1-T01).
