# 10. Chiến lược test, rủi ro, lộ trình học (M1-T10)

Trạng thái: bản nháp chờ duyệt. Gồm: chiến lược test, chiến lược tích hợp, rủi ro kỹ thuật bổ sung, lộ trình học gắn milestone và gate đo được cho M2 đến M9. Gate **không** chứa ngưỡng điểm tự đặt; ngưỡng chất lượng chỉ được đặt sau khi có baseline (M6).

## 1. Chiến lược test

### 1.1 Ba tầng test

| Tầng | Phạm vi | Công cụ | Dữ liệu và provider | Chạy khi |
|------|---------|---------|---------------------|----------|
| **Unit** | Hàm và lớp riêng lẻ, không DB, không mạng | pytest | Dữ liệu tự dựng nhỏ; provider **giả** (fake) | Mỗi lần commit |
| **Integration** | Nhiều thành phần với **PostgreSQL + pgvector thật** (test database), qua FastAPI test client | pytest, httpx hoặc test client của FastAPI | DB test riêng, provider giả | Cuối mỗi task có DB hoặc API; trước mỗi gate |
| **End-to-end (E2E)** | Cả stack như người dùng: đăng nhập, upload, hỏi, evaluation, security, báo cáo | Docker Compose; Playwright hoặc kịch bản gọi API tùy chọn; ít nhất một lượt chạy với provider thật | Tài liệu mẫu nhỏ, provider thật cho một lượt | M9 và trước demo |

Provider giả (fake embedder, fake LLM, fake judge) là bắt buộc: test nhanh, miễn phí, tái lập được, và cho phép gây lỗi có chủ đích (timeout, rate limit, câu trả lời sai).

### 1.2 Phải test những gì (theo module)

| Module | Unit | Integration | Ghi chú |
|--------|------|-------------|---------|
| Auth | Hash và kiểm tra mật khẩu, tạo và giải mã JWT | Đăng ký, đăng nhập đúng và sai, endpoint từ chối không token | |
| Ingestion | Parser mỗi định dạng (file mẫu, file hỏng), cleaner, chunker (kích thước, overlap, metadata) | Upload tới lưu vector với embedder giả; trùng, xóa, reprocess, trạng thái failed | File hỏng không làm sập tiến trình |
| Cô lập dữ liệu | | **User A không thấy, sửa, xóa tài nguyên của B qua API; retrieval không trả chunk của B** | Quan trọng nhất; chạy ở M3 và M4 |
| RAG | Context builder, xử lý thiếu context, dựng prompt | Pipeline với provider giả; gọi pipeline từ script độc lập (không FastAPI) | Test câu hỏi không có đáp án phải trả "không đủ thông tin" |
| Dataset | Validate schema, loader import | Tạo version, duyệt, **sửa version đã duyệt bị từ chối** | |
| Retrieval metrics | So kết quả với ví dụ **tự tính tay** | | Hàm thuần |
| Generation metrics, judge | Parse đầu ra judge, xử lý judge lỗi | Với judge giả | Judge thật chỉ chạy ở bước kiểm chứng riêng |
| Evaluation runner | Tổng hợp | Một case lỗi không làm hỏng run; metadata run đầy đủ | |
| Security | Loader validate YAML; evaluator ca pass và fail (canary token) | Chạy bộ test mẫu qua pipeline; test Access Control với hai user | |
| Benchmark | | Hai cấu hình trên cùng dataset version; run con có metadata | |
| Báo cáo | | Nội dung CSV khớp DB | |
| Lỗi hệ thống | | Timeout, rate limit, lỗi DB, retry có giới hạn | Dùng provider giả gây lỗi |

### 1.3 Nguyên tắc

- Test không gọi provider thật, trừ các bước kiểm chứng ghi rõ (có chi phí).
- Mỗi task kết thúc bằng test của chính nó chạy xanh trước khi sang task tiếp.
- Test lỗi quan trọng ngang test đường đi đúng (NFR-07).
- Kết quả đo chất lượng (metric, benchmark) là **số đo**, không phải test pass/fail; chỉ kiểm tra tính đúng của cách tính, không khẳng định "tốt".
- Ghi kết quả test thật vào `progress_log.md` (lệnh đã chạy, số test, kết quả).

## 2. Chiến lược tích hợp

| Nguyên tắc | Cách làm |
|------------|----------|
| Tích hợp theo chiều dọc | Mỗi milestone đưa một lát cắt chạy được từ DB tới giao diện (ví dụ M3 từ upload tới danh sách tài liệu), không dựng hết backend rồi mới nối frontend |
| Hợp đồng trước | API theo `08_api_contracts.md`; đổi API thì sửa tài liệu trước, sau đó code backend và frontend |
| Một pipeline | `rag_pipeline.py` được viết ở M4 độc lập với FastAPI, sau đó Chat, Evaluation, Security gọi lại. Review "không có logic RAG ngoài `ai_engine/pipeline/`" ở mỗi gate từ M4 |
| Ranh giới phụ thuộc | Theo mục 4 của `09_repo_manifest.md`; `ai_engine`, `evaluation`, `security` không import `backend/app` |
| Provider giả ở ranh giới interface | Fake cài đúng `base_embedder.py`, `base_llm_client.py` |
| Migration có kỷ luật | Mỗi thay đổi schema là một migration Alembic; kiểm tra `upgrade` trên DB sạch trước mỗi gate |
| Cấu hình thống nhất | Backend lấy tham số từ `core/config.py`; `ai_engine`, `evaluation`, `security` nhận tham số qua đối số do Service truyền vào; không đọc biến môi trường rải rác |
| Kiểm tra tương thích | Mỗi gate rà: import, package, biến môi trường, đường dẫn Docker, migration, API contract, tương thích frontend và backend (theo `CLAUDE.md`) |

Thứ tự tích hợp: DB, Auth, Ingestion, Retriever, Pipeline, Chat, Dataset, Evaluation runner, Security runner, Benchmark runner, Báo cáo.

## 3. Rủi ro kỹ thuật bổ sung

Rủi ro tổng quan R1 đến R8 nằm ở `01_feasibility.md`. Bổ sung các rủi ro kỹ thuật phát sinh từ thiết kế:

| # | Rủi ro | Hậu quả | Giảm thiểu | Xác nhận ở |
|---|--------|---------|------------|------------|
| R9 | Tác vụ nền (ingestion, evaluation, security run, benchmark run) mất khi backend khởi động lại | Document hoặc run kẹt ở `processing` hoặc `running` | Cơ chế phát hiện quá hạn và đánh dấu failed để chạy lại; ghi vào tài liệu giới hạn | M3-T07, M6-T06, M7-T07, M8-T03 |
| R10 | Lọc `user_id` kết hợp chỉ mục vector gần đúng làm trả thiếu kết quả | Retrieval bỏ sót chunk liên quan | Đo trên dữ liệu thật; MVP có thể dùng quét chính xác khi dữ liệu nhỏ | M3, M4 |
| R11 | Đổi embedding model làm cột vector không khớp số chiều | Phải embed lại toàn bộ | Chốt provider và gọi thử một lần trước M3-T01 (điều kiện vào M3-T01); lưu `embedding_model` mỗi chunk | M3-T01 |
| R12 | Reference context trong dataset không khớp chunk khi đổi cách chunk | Metric retrieval sai | Reference theo khoảng ký tự trong tài liệu (không theo chunk id); kiểm tra bằng test với hai kích thước chunk | M5, M6-T02 |
| R13 | PDF phức tạp trích văn bản kém (bảng, cột, ảnh quét) | Dataset và đánh giá dựa trên văn bản sai | Chọn tài liệu corpus phù hợp; ghi giới hạn parser; OCR là out-of-scope | M3-T04, M5-T03 |
| R14 | Giá và tên model của provider thay đổi | Chi phí ước tính lệch, cấu hình hỏng | Ghi thời điểm lấy giá; model và giá đặt trong `configs/models.yaml`, không rải trong code | M4, M8-T04 |
| R15 | Kết quả đánh giá bị rò rỉ dữ liệu giữa lần chạy (prompt hoặc test case lộ cho model sinh) | Điểm cao giả | Giữ ground truth ngoài prompt sinh; review prompt khi viết | M4-T04, M6-T03 |
| R16 | Test bảo mật sai phạm vi hoặc tạo dữ liệu thật | Rủi ro đạo đức | Chỉ dùng dữ liệu giả và canary token; môi trường test cô lập | M7-T01 |
| R17 | Không gian lỗi quá lớn khiến mất thời gian debug | Chậm tiến độ | Log có cấu trúc, `error_message` theo từng bản ghi, lỗi chuẩn hóa | M2-T07 |
| R18 | Dò mật khẩu đăng nhập (brute force) vì chưa giới hạn số lần thử | Kẻ tấn công thử nhiều mật khẩu cho một email | Băm bằng argon2 (chậm có chủ đích), thông báo lỗi chung; giới hạn tần suất đăng nhập là Deferred, cần bổ sung trước khi mở ra Internet | M3-T02 (chấp nhận cho MVP chạy cục bộ), M9-T07 |
| R19 | Token JWT không thu hồi được trước khi hết hạn | User bị khóa vẫn dùng được token cũ đến hết hạn | Mỗi request kiểm tra lại `is_active` trong DB (đã làm); đặt thời hạn token ngắn (`JWT_EXPIRE_MINUTES`) | M3-T02 |

## 4. Lộ trình học gắn milestone

Độ phức tạp: T thấp, TB trung bình, C cao. Học theo nhu cầu của task, không học trước hết mọi thứ.

| Milestone | Cần học để làm được | Kết quả học kiểm chứng được | Phức tạp |
|-----------|---------------------|-----------------------------|----------|
| M1. Analysis & Design | Kiến trúc phân tầng, Modular Monolith, Mermaid, thiết kế REST, quan hệ CSDL | Giải thích được vì sao chọn kiến trúc và vẽ lại sơ đồ không nhìn tài liệu | TB |
| M2. Foundation | Git và quy ước commit; Docker, Compose, volume, healthcheck; FastAPI cơ bản; biến môi trường; SQLAlchemy và Alembic; pgvector là gì | Giải thích `docker compose up` làm gì; viết được một migration | TB |
| M3. Ingestion | JWT và hash mật khẩu; upload file an toàn; parse PDF, DOCX; chunking (kích thước, overlap, đánh đổi); embedding là gì, khoảng cách vector; retry, backoff; giao dịch DB | Giải thích vì sao chunk size ảnh hưởng truy xuất; viết test cô lập user | TB đến C |
| M4. RAG | Retrieval bằng vector search, Top-K; thiết kế prompt, grounding, trích dẫn; hallucination và xử lý thiếu context; token và ước tính chi phí; prompt injection ở mức khái niệm | Gọi được pipeline từ script độc lập; giải thích mỗi bước pipeline | C |
| M5. Dataset | Thiết kế bộ test đánh giá; loại câu hỏi (fact, multi-hop, không đáp án); reference context; độ tin cậy của ground truth; versioning dữ liệu | Viết được case tốt và giải thích vì sao case yếu làm metric sai | C (tốn công) |
| M6. Evaluation | Precision@K, Recall@K, MRR, NDCG@K (tính tay); Faithfulness, Answer Relevancy, Context Precision, Context Recall; LLM-as-a-Judge và thiên lệch; Ragas, DeepEval ở mức hiểu cách tính; phân tích lỗi | Tính tay metric khớp code; nêu được ít nhất 3 giới hạn của judge | C |
| M7. Security | Prompt injection, jailbreak, rò rỉ dữ liệu, kiểm soát truy cập, tài liệu độc hại; threat model; canary token; thang severity; đạo đức kiểm thử | Phân loại được một kịch bản vào đúng nhóm và đánh giá đúng pass hay fail | C |
| M8. Benchmark & Reporting | Thiết kế thí nghiệm (đổi một biến); đọc kết quả có ràng buộc; ước tính chi phí; xuất CSV | Giải thích vì sao kết luận benchmark chỉ đúng trong điều kiện đã ghi | TB |
| M9. Final Integration | Pyramid test, E2E, triển khai sạch bằng Compose, viết tài liệu và demo | Máy sạch chạy được theo README; trình bày demo 5 đến 10 phút | TB |

## 5. Acceptance criteria và gate đo được cho M2 đến M9

Mỗi mục là điều kiện **kiểm tra được** (có lệnh hoặc quan sát cụ thể). Gate chỉ đạt khi mọi dòng đều đạt, hoặc có ngoại lệ được bạn đồng ý bằng văn bản trong `progress_log.md`.

### Gate M2. Foundation

| # | Điều kiện | Cách kiểm tra |
|---|-----------|---------------|
| 1 | Máy sạch clone repo, làm theo README là chạy được toàn bộ stack | Thử trên thư mục hoặc máy mới |
| 2 | `docker compose up` đưa `db` và `backend` về trạng thái healthy | `docker compose ps` |
| 3 | `GET /health` trả 200 và báo trạng thái DB | Gọi bằng curl |
| 4 | Dữ liệu DB còn sau khi `docker compose down` rồi `up` | Tạo bản ghi, restart, kiểm tra |
| 5 | `alembic upgrade head` chạy sạch và extension `vector` hoạt động | Truy vấn kiểm tra extension |
| 6 | Frontend hiển thị trạng thái backend qua lớp `services/api` | Mở trình duyệt |
| 7 | Lỗi trả về theo một định dạng JSON thống nhất; `pytest` chạy được với test `/health` | Chạy `pytest` |
| 8 | Không có secret trong Git history; `.env` bị ignore | Quét repo và lịch sử |

**Điều kiện vào M3-T01** (đã chốt 2026-11-05): embedding model là `intfloat/multilingual-e5-small`, 384 chiều, chạy cục bộ (`06_deployment_tech.md` mục 4). Số chiều mới xác minh từ cấu hình chính thức; test khẳng định số chiều thật khi chạy model nằm ở M3-T06.

### Gate M3. Ingestion

| # | Điều kiện | Cách kiểm tra |
|---|-----------|---------------|
| 1 | Đăng ký, đăng nhập đúng và sai; endpoint bảo vệ từ chối không token | Test API |
| 2 | Upload file sai loại hoặc quá lớn bị từ chối với lỗi rõ | Test API |
| 3 | PDF, DOCX, TXT mẫu xử lý tới `ready`; chunk và vector đúng `document_id`, `user_id` | Test integration, kiểm tra DB |
| 4 | File hỏng dẫn tới `failed` kèm lý do, tiến trình không sập | Test với file hỏng |
| 5 | Upload trùng, xóa (chunk và file gốc biến mất), reprocess (không chunk trùng) đúng như `05_sequences.md` | Test integration |
| 6 | **User A không thấy tài liệu của user B** | Test cô lập |
| 7 | Test unit và integration của ingestion xanh; manifest cập nhật | Chạy `pytest`, đối chiếu manifest |

### Gate M4. RAG

| # | Điều kiện | Cách kiểm tra |
|---|-----------|---------------|
| 1 | Chat chạy end-to-end: hỏi, nhận câu trả lời kèm citation | Thử tay và test integration |
| 2 | **Retrieval không bao giờ trả chunk của user khác**, kể cả khi câu hỏi nhắm vào nội dung đó | Test cô lập bắt buộc |
| 3 | Câu hỏi không có đáp án trong tài liệu nhận câu "không đủ thông tin" | Test với tập câu hỏi không có đáp án |
| 4 | Pipeline gọi được từ script độc lập, không phụ thuộc FastAPI | Chạy script |
| 5 | Mỗi lượt hỏi lưu chunk kèm điểm, cấu hình, latency, token, chi phí ước tính (nêu cách ước tính) | Kiểm tra DB |
| 6 | Có baseline thủ công khoảng 20 câu trên tài liệu thật, **số liệu thật** ghi trong `docs/baseline_manual.md` | Đọc file |

### Gate M5. Dataset

| # | Điều kiện | Cách kiểm tra |
|---|-----------|---------------|
| 1 | Có ít nhất một dataset version `reviewed` dùng được cho M6 | Kiểm tra DB và API |
| 2 | Khoảng 100 case, đa dạng loại và độ khó, có tỷ lệ câu không có đáp án | Thống kê theo `question_type`, `difficulty` |
| 3 | Mỗi case có reference context kiểm chứng được trên tài liệu thật | Rà soát mẫu |
| 4 | Version đã duyệt không sửa được; sửa thì tạo version mới | Test |
| 5 | Danh sách tài liệu corpus kèm nguồn và quyền sử dụng được ghi trong `docs/` | Đọc file |

### Gate M6. Evaluation

| # | Điều kiện | Cách kiểm tra |
|---|-----------|---------------|
| 1 | Bốn retrieval metric khớp ví dụ tính tay | Unit test |
| 2 | Ít nhất hai generation metric chạy trên case mẫu, ghi rõ judge model và prompt của judge | Chạy mẫu, xem metadata |
| 3 | Runner dùng đúng pipeline của Chat; một case lỗi không làm hỏng run | Review code và test |
| 4 | Một run baseline đầy đủ metadata (dataset version, model, embedding, prompt version, chunk size, overlap, Top-K, temperature, framework version, timestamp) | Kiểm tra bản ghi |
| 5 | Chạy lại với cùng cấu hình tái tạo được metadata; nêu mức chênh kết quả đo được | Chạy lại và so sánh |
| 6 | Có phân tích lỗi thật và mức đồng thuận judge-người (ghi đúng số đo được) trong `docs/error_analysis.md` | Đọc file |
| 7 | **Mọi điểm trong báo cáo đến từ run thật** | Đối chiếu báo cáo với DB |

### Gate M7. Security

| # | Điều kiện | Cách kiểm tra |
|---|-----------|---------------|
| 1 | Có phạm vi, quy tắc và threat model trong `docs/security_scope.md` | Đọc file |
| 2 | Mỗi nhóm trong 5 nhóm có test case, có lý do tồn tại | Rà thư mục `security/test_cases/` |
| 3 | Runner chạy bộ test qua đúng pipeline của Chat và lưu evidence | Chạy và kiểm tra DB |
| 4 | Evaluator có test cho cả trường hợp pass và fail | Unit test |
| 5 | Chạy lại bộ test cho kết quả lưu lại và lặp lại được | Chạy hai lần |
| 6 | Báo cáo nêu phát hiện, mitigation và phần chưa kiểm tra; **không** dùng cụm "an toàn tuyệt đối" | Đọc báo cáo |

### Gate M8. Benchmark & Reporting

| # | Điều kiện | Cách kiểm tra |
|---|-----------|---------------|
| 1 | Có `docs/benchmark_design.md`: bảng cấu hình, biến thay đổi, biến cố định | Đọc file |
| 2 | Benchmark thật so sánh ít nhất 2 cấu hình trên cùng dataset version | Kiểm tra bản ghi |
| 3 | So sánh được chất lượng, độ trễ, token, chi phí; ghi cách tính chi phí và thời điểm giá | Đọc báo cáo |
| 4 | File CSV xuất ra khớp dữ liệu trong DB, kèm metadata | So sánh mẫu |
| 5 | Kết luận chỉ dựa trên số đo thật và nêu giới hạn | Đọc kết luận |

### Gate M9. Final Integration

| # | Điều kiện | Cách kiểm tra |
|---|-----------|---------------|
| 1 | Unit test của module lõi (chunking, metric, evaluator, quyền retrieval) và các lỗi parsing, provider, rate limit, timeout xanh | `pytest` |
| 2 | Integration test cho ingestion, chat, evaluation, security chạy trên DB thật | `pytest` |
| 3 | E2E: đăng nhập, upload, hỏi, evaluation, security, xem báo cáo | Chạy kịch bản |
| 4 | Máy mới chỉ cần clone, điền `.env`, `docker compose up` | Thử trên máy mới |
| 5 | README đầy đủ; sơ đồ khớp với code | Đối chiếu |
| 6 | Có kịch bản demo 5 đến 10 phút, chỉ nêu số liệu thật | Đọc kịch bản |
| 7 | Audit cuối: chỉ một RAG pipeline; không secret trong code hay Git history; cô lập user được test; mọi kết quả tái lập được từ metadata; manifest khớp file thực tế; giới hạn được ghi rõ | Checklist M9-T07 |

## 6. Phản biện các giả định về chất lượng và test

| Giả định | Vì sao yếu | Cách xử lý |
|----------|-----------|------------|
| "Test xanh nghĩa là hệ thống tốt" | Test xanh chỉ nói code làm đúng điều ta *nghĩ tới*; không nói RAG trả lời hay | Tách rõ test (đúng/sai của code) và evaluation (đo chất lượng); không dùng điểm metric làm test pass/fail khi chưa có baseline |
| "Provider giả đủ giống provider thật" | Provider thật có độ trễ, lỗi lạ, hành vi thay đổi | Giữ ít nhất một lượt chạy E2E với provider thật có chủ đích (M9-T03) và ghi lại |
| "Điểm LLM judge cao nghĩa là câu trả lời tốt" | Judge có thiên lệch và không ổn định | Chấm tay một mẫu và ghi mức đồng thuận thật (M6-T07) |
| "Test cô lập user một lần là đủ" | Lỗi lọc quyền có thể xuất hiện khi thêm tính năng mới | Test cô lập chạy trong mọi lần chạy test đầy đủ, không phải một lần |
| "Gate ghi trong tài liệu sẽ tự được tuân thủ" | Dễ bỏ qua khi trễ tiến độ | Mỗi gate ghi lệnh kiểm tra cụ thể và kết quả thật vào `progress_log.md`; ngoại lệ phải ghi lý do |

## 7. Giải thích khái niệm cho người mới

- **Fake, mock, stub**: bản thay thế của một thành phần thật trong test. "Provider giả" ở đây là một lớp cài cùng interface nhưng trả kết quả định sẵn (hoặc gây lỗi có chủ đích), giúp test nhanh, miễn phí và lặp lại được.
- **Test pyramid**: nhiều unit test (nhanh, rẻ, chỉ ra đúng chỗ lỗi), ít hơn integration test (chạy với DB thật), ít nhất là E2E (chậm, dễ vỡ nhưng bắt lỗi ghép nối). Đảo ngược kim tự tháp làm bộ test chậm và khó sửa.
- **Baseline**: kết quả của phiên bản đơn giản đầu tiên, dùng làm mốc so sánh. Không có baseline thì "tốt hơn" hay "tệ hơn" không có nghĩa; đó là lý do dự án cấm đặt ngưỡng điểm trước khi có baseline.
- **Tái lập (reproducibility)**: cùng dữ liệu và cùng cấu hình cho cùng kết quả hoặc cùng mức dao động đã biết. LLM có tính ngẫu nhiên nên ta ghi metadata đủ để chạy lại và ghi nhận độ chênh, không giả định kết quả giống hệt.
- **Gate (cổng)**: điều kiện kiểm tra được để được sang giai đoạn tiếp theo, tránh xây tiếp trên nền chưa vững.
- **Canary token**: chuỗi bí mật giả đặt vào dữ liệu thử nghiệm; nếu nó xuất hiện trong câu trả lời thì biết chắc dữ liệu đã bị rò rỉ. Cho phép phát hiện bằng luật xác định thay vì phải nhờ LLM đoán.

## 8. Điều kiện kiểm chứng của tài liệu này

- Mỗi milestone M2 đến M9 có gate với các điều kiện kiểm tra được (mục 5).
- Không có ngưỡng điểm hay con số hiệu năng tự đặt.
- Các rủi ro R9 trở đi đều gắn với task xác nhận.
