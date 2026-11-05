# 08. Đặc tả API (M1-T08)

Trạng thái: bản nháp chờ duyệt. Đây là hợp đồng giữa frontend và backend; đổi hợp đồng thì sửa tài liệu này trước. Tên trường khớp với `07_database.md`. Giới hạn cụ thể (dung lượng file, số lần retry) là cấu hình, không cố định ở đây.

## 1. Quy ước chung

| Mục | Quy ước |
|-----|---------|
| Base path | `/api/v1` (riêng `/health` nằm ngoài) |
| Định dạng | JSON (trừ upload là `multipart/form-data` và export là `text/csv`) |
| Xác thực | Header `Authorization: Bearer <JWT>`. Cột **Auth** ở dưới: `Không` hoặc `Có` |
| Phân quyền | Tài nguyên phải thuộc user hiện tại; không thuộc thì trả **404** (không lộ sự tồn tại) |
| ID | UUID dạng chuỗi |
| Thời gian | ISO 8601, UTC |
| Phân trang | Query `limit` và `offset`; response dạng `{ "items": [...], "total": n, "limit": n, "offset": n }` |
| Tác vụ dài | Trả `202 Accepted` kèm id; frontend poll `GET` chi tiết để xem `status` |
| Đặt tên | Đường dẫn danh từ số nhiều, kebab-case; trường JSON snake_case |
| Báo cáo | Endpoint `.../report?format=csv` sinh CSV tức thì và trả thẳng; backend ghi một bản ghi lịch sử vào bảng `reports`, không lưu file |

### Định dạng lỗi thống nhất

```json
{
  "error": {
    "code": "validation_error",
    "message": "Mô tả ngắn cho người dùng",
    "details": [{ "field": "email", "issue": "định dạng không hợp lệ" }]
  }
}
```

| HTTP | `code` | Khi nào |
|------|--------|---------|
| 400 | `bad_request` | Yêu cầu sai logic nghiệp vụ |
| 401 | `unauthorized` | Thiếu hoặc sai token, token hết hạn |
| 404 | `not_found` | Không tồn tại hoặc không thuộc user |
| 409 | `conflict` | Trùng (email, document trùng hash), hoặc vi phạm trạng thái (sửa version đã duyệt) |
| 413 | `file_too_large` | File vượt giới hạn |
| 415 | `unsupported_file_type` | Loại file không được phép |
| 422 | `validation_error` | Dữ liệu không hợp lệ theo schema |
| 429 | `rate_limited` | Provider hoặc hệ thống giới hạn tần suất |
| 502 | `provider_error` | Lỗi từ LLM hoặc embedding provider sau khi hết retry |
| 500 | `internal_error` | Lỗi không lường trước; không lộ chi tiết nội bộ |

### Luồng xử lý một request

```
Router (nhận request, validate schema Pydantic)
  -> Dependency (xác thực JWT, lấy current_user)
    -> Service (use case, kiểm tra quyền sở hữu, điều phối)
      -> AI Engine / Evaluation / Security (logic miền, dùng chung RAG Pipeline)
        -> Repository (truy cập DB, luôn lọc theo user_id)
          -> Response (schema Pydantic, không lộ password_hash hay lỗi nội bộ)
```

Router **không** chứa logic nghiệp vụ; Service **không** truy cập DB trực tiếp.

## 2. Health

| Method | Path | Mục đích | Auth | Response | Lỗi |
|--------|------|----------|------|----------|-----|
| GET | `/health` | Kiểm tra backend và kết nối DB | Không | `200 {"status":"ok","database":"ok"}` | `503` nếu DB không kết nối được |

## 3. Authentication

| Method | Path | Mục đích | Auth | Request | Response | Validation | Lỗi |
|--------|------|----------|------|---------|----------|------------|-----|
| POST | `/auth/register` | Đăng ký | Không | `{ "email", "password" }` | `201 { "id", "email", "created_at" }` | Email đúng định dạng và chưa tồn tại; mật khẩu đạt độ dài tối thiểu theo cấu hình | 409 email trùng, 422 |
| POST | `/auth/login` | Đăng nhập | Không | `{ "email", "password" }` | `200 { "access_token", "token_type": "bearer", "expires_in" }` | Có đủ hai trường | 401 sai thông tin (thông báo chung, không tiết lộ email có tồn tại hay không) |
| GET | `/auth/me` | Thông tin user hiện tại | Có | không | `200 { "id", "email", "created_at" }` | | 401 |

## 4. Documents

| Method | Path | Mục đích | Auth | Request | Response | Validation | Lỗi |
|--------|------|----------|------|---------|----------|------------|-----|
| POST | `/documents` | Upload tài liệu | Có | `multipart/form-data`, trường `file` | `202 Document` (status `uploaded`) | Loại file PDF, DOCX, TXT; dung lượng trong giới hạn; file không rỗng | 409 trùng (kèm `existing_document_id`), 413, 415, 422 |
| GET | `/documents` | Liệt kê document của user | Có | Query: `status`, `limit`, `offset` | `200 { items: [Document], ... }` | `status` thuộc danh sách hợp lệ | 401 |
| GET | `/documents/{document_id}` | Chi tiết và trạng thái xử lý | Có | | `200 Document` | UUID hợp lệ | 404 |
| DELETE | `/documents/{document_id}` | Xóa document, chunk, file gốc | Có | | `204` | | 404 |
| POST | `/documents/{document_id}/reprocess` | Xử lý lại | Có | tùy chọn `{ "chunk_size", "chunk_overlap" }` | `202 Document` (status `processing`) | `chunk_size` lớn hơn `chunk_overlap`, trong khoảng cấu hình | 404, 409 nếu đang processing, 422 |

`Document`:
```json
{
  "id": "uuid", "filename": "policy.pdf", "content_type": "application/pdf",
  "size_bytes": 123456, "status": "uploaded|processing|ready|failed",
  "error_message": null, "chunk_count": 0,
  "processing_config": { "chunk_size": 0, "chunk_overlap": 0, "embedding_model": "..." },
  "created_at": "...", "updated_at": "..."
}
```

## 5. Model configurations

Cần cho Chat, Evaluation, Security và Benchmark. Cấu hình bất biến nên **không có** endpoint sửa. Cấu hình mặc định của Chat: khi `model_configuration_id` bỏ trống, `model_config_service` dùng một bản ghi tạo từ `configs/rag_default.yaml` (tạo ở lần dùng đầu).

| Method | Path | Mục đích | Auth | Request | Response | Validation | Lỗi |
|--------|------|----------|------|---------|----------|------------|-----|
| POST | `/model-configurations` | Tạo cấu hình | Có | `{ "name", "llm_provider", "llm_model", "embedding_provider", "embedding_model", "prompt_version", "top_k", "temperature", "chunk_size", "chunk_overlap" }` | `201 ModelConfiguration` | `top_k` nguyên dương; `temperature` trong khoảng hợp lệ; provider và model thuộc danh sách được hỗ trợ | 422 |
| GET | `/model-configurations` | Liệt kê | Có | `limit`, `offset` | `200 { items }` | | |
| GET | `/model-configurations/{id}` | Chi tiết | Có | | `200 ModelConfiguration` | | 404 |

## 6. Chat

| Method | Path | Mục đích | Auth | Request | Response | Validation | Lỗi |
|--------|------|----------|------|---------|----------|------------|-----|
| POST | `/chat/messages` | Gửi câu hỏi, nhận câu trả lời | Có | `{ "question", "session_id"?, "model_configuration_id"? }` | `200 ChatAnswer` | Câu hỏi không rỗng, độ dài trong giới hạn; `session_id` (nếu có) thuộc user | 404 session, 422, 429, 502 |
| GET | `/chat/sessions` | Liệt kê session | Có | `limit`, `offset` | `200 { items: [{id,title,created_at}] }` | | |
| GET | `/chat/sessions/{session_id}/messages` | Lấy message của session | Có | | `200 { items: [ChatMessage] }` | | 404 |
| DELETE | `/chat/sessions/{session_id}` | Xóa session | Có | | `204` | | 404 |

`ChatAnswer`:
```json
{
  "session_id": "uuid",
  "message_id": "uuid",
  "answer": "…",
  "insufficient_context": false,
  "citations": [
    { "chunk_id": "uuid|null", "document_id": "uuid|null", "filename": "policy.pdf",
      "page_number": 3, "score": 0.0, "snippet": "…" }
  ],
  "metrics": { "latency_ms": 0, "prompt_tokens": 0, "completion_tokens": 0, "estimated_cost": 0.0 },
  "model_configuration_id": "uuid"
}
```
Khi bằng chứng không đủ: `insufficient_context = true`, `answer` nói không đủ thông tin, `citations` rỗng hoặc chỉ gồm các chunk liên quan yếu.

## 7. Datasets

| Method | Path | Mục đích | Auth | Request | Response | Validation | Lỗi |
|--------|------|----------|------|---------|----------|------------|-----|
| POST | `/datasets` | Tạo dataset (kèm version 1 ở trạng thái draft) | Có | `{ "name", "description"? }` | `201 Dataset` | `name` không rỗng | 422 |
| GET | `/datasets` | Liệt kê | Có | `limit`, `offset` | `200 { items }` | | |
| GET | `/datasets/{dataset_id}` | Chi tiết | Có | | `200 Dataset` | | 404 |
| POST | `/datasets/{dataset_id}/versions` | Tạo version mới | Có | `{ "copy_from_version_id"?, "notes"? }` | `201 DatasetVersion` (draft) | Version nguồn thuộc cùng dataset | 404, 422 |
| GET | `/datasets/{dataset_id}/versions` | Liệt kê version | Có | | `200 { items }` | | 404 |
| POST | `/dataset-versions/{version_id}/review` | Đánh dấu đã duyệt và đóng băng | Có | | `200 DatasetVersion` (reviewed) | Phải có ít nhất một test case | 404, 409 đã reviewed, 422 |
| GET | `/dataset-versions/{version_id}/test-cases` | Liệt kê test case | Có | `question_type`, `difficulty`, `limit`, `offset` | `200 { items: [TestCase] }` | Giá trị lọc hợp lệ | 404 |
| POST | `/dataset-versions/{version_id}/test-cases` | Thêm test case | Có | `TestCaseInput` | `201 TestCase` | Xem dưới | 404, 409 version đã reviewed, 422 |
| POST | `/dataset-versions/{version_id}/test-cases/import` | Import hàng loạt CSV hoặc JSON | Có | `multipart/form-data`, trường `file` | `200 { "imported": n }` khi mọi dòng hợp lệ | Validate **toàn bộ** file trước khi ghi; có bất kỳ dòng sai nào thì không ghi gì cả và trả `422` kèm `details: [{ "row", "issue" }]` | 404, 409, 415, 422 |
| PUT | `/test-cases/{test_case_id}` | Sửa test case | Có | `TestCaseInput` | `200 TestCase` | Như thêm mới | 404, 409 version đã reviewed |
| DELETE | `/test-cases/{test_case_id}` | Xóa test case | Có | | `204` | | 404, 409 version đã reviewed |

`TestCaseInput`:
```json
{
  "question": "…",
  "ground_truth_answer": "… hoặc null với câu không có đáp án",
  "reference_contexts": [
    { "document_content_hash": "…", "char_start": 0, "char_end": 0, "text": "…" }
  ],
  "source_note": "…",
  "question_type": "fact|multi_hop|summarization|unanswerable",
  "difficulty": "easy|medium|hard",
  "expected_behavior": "answer|insufficient_context"
}
```
Quy tắc: `question` không rỗng; nếu `expected_behavior = answer` thì `ground_truth_answer` và `reference_contexts` bắt buộc có; nếu `insufficient_context` thì `ground_truth_answer` để trống.

## 8. Evaluation

| Method | Path | Mục đích | Auth | Request | Response | Validation | Lỗi |
|--------|------|----------|------|---------|----------|------------|-----|
| POST | `/evaluations` | Tạo và bắt đầu một run | Có | `{ "dataset_version_id", "model_configuration_id", "judge_model", "judge_prompt_version" }` | `202 EvaluationRun` (status `pending`) | Version phải ở trạng thái `reviewed`; cấu hình thuộc user; cấu hình corpus khớp tài liệu hiện có (nếu lệch thì vẫn chạy và ghi cảnh báo vào `environment` của run) | 404, 409 version chưa duyệt, 422 |
| GET | `/evaluations` | Liệt kê run | Có | `status`, `dataset_version_id`, `limit`, `offset` | `200 { items }` | | |
| GET | `/evaluations/{run_id}` | Chi tiết, tiến độ, điểm tổng hợp | Có | | `200 EvaluationRun` | | 404 |
| GET | `/evaluations/{run_id}/results` | Kết quả từng case | Có | `status`, `limit`, `offset` | `200 { items: [EvaluationResult] }` | | 404 |
| GET | `/evaluations/{run_id}/report` | Xuất báo cáo | Có | Query `format=csv` | `200 text/csv` | `format` thuộc danh sách hỗ trợ | 404, 422, 409 nếu run chưa hoàn tất |

`EvaluationRun`:
```json
{
  "id": "uuid", "status": "pending|running|completed|failed",
  "dataset_version_id": "uuid", "model_configuration_id": "uuid", "benchmark_run_id": null,
  "judge_model": "…", "judge_prompt_version": "…",
  "progress": { "total_cases": 0, "completed_cases": 0, "failed_cases": 0 },
  "aggregate_metrics": [ { "metric_name": "precision_at_k", "k": 5, "value": 0.0, "method": "deterministic" } ],
  "environment": { "...": "..." },
  "started_at": "…", "finished_at": null
}
```
`aggregate_metrics` chỉ chứa metric đã tính được; metric lỗi có `value: null` và `status: "failed"`, không điền số giả.

## 9. Security

| Method | Path | Mục đích | Auth | Request | Response | Validation | Lỗi |
|--------|------|----------|------|---------|----------|------------|-----|
| GET | `/security/test-cases` | Liệt kê test case khả dụng | Có | `category` | `200 { items }` | | |
| POST | `/security/runs` | Bắt đầu run | Có | `{ "model_configuration_id", "categories"?: [..] }` | `202 SecurityRun` | Danh mục thuộc 5 nhóm hợp lệ; cấu hình thuộc user | 404, 422 |
| GET | `/security/runs` | Liệt kê run | Có | `limit`, `offset` | `200 { items }` | | |
| GET | `/security/runs/{run_id}` | Chi tiết, tổng hợp, giới hạn độ phủ | Có | | `200 SecurityRun` (kèm `coverage_notes`) | | 404 |
| GET | `/security/runs/{run_id}/results` | Kết quả từng test case | Có | `status`, `severity`, `category` | `200 { items: [SecurityResult] }` | | 404 |
| GET | `/security/runs/{run_id}/report` | Xuất báo cáo | Có | `format=csv` | `200 text/csv` | | 404, 409 |

`SecurityResult`: `{ "test_case_id", "category", "title", "status": "pass|fail|error", "severity", "actual_response", "evidence", "evaluator": "rule|judge", "mitigation" }`.

## 10. Benchmarks

| Method | Path | Mục đích | Auth | Request | Response | Validation | Lỗi |
|--------|------|----------|------|---------|----------|------------|-----|
| POST | `/benchmarks` | Tạo và bắt đầu benchmark | Có | `{ "name", "dataset_version_id", "varied_variable", "model_configuration_ids": [..], "judge_model", "judge_prompt_version" }` | `202 BenchmarkRun` | `varied_variable` thuộc {`llm_model`, `top_k`, `prompt_version`} (giá trị khác trả `422`); ít nhất 2 cấu hình; version đã `reviewed`; các cấu hình chỉ khác nhau ở biến đã khai báo (cảnh báo nếu khác nhiều biến) | 404, 409, 422 |
| GET | `/benchmarks` | Liệt kê | Có | `limit`, `offset` | `200 { items }` | | |
| GET | `/benchmarks/{benchmark_id}` | Chi tiết, các run con, so sánh chất lượng, độ trễ, token, chi phí | Có | | `200 BenchmarkRun` | | 404 |
| GET | `/benchmarks/{benchmark_id}/report` | Xuất báo cáo | Có | `format=csv` | `200 text/csv` | | 404, 409 |

## 11. Ánh xạ trang giao diện tới endpoint

| Trang frontend | Endpoint sử dụng |
|----------------|------------------|
| Login / Register | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Dashboard | `GET /documents`, `GET /chat/sessions`, `GET /datasets`, `GET /evaluations`, `GET /security/runs`, `GET /benchmarks` (lấy tóm tắt) |
| Documents | `POST /documents`, `GET /documents`, `GET /documents/{id}` (poll trạng thái), `DELETE /documents/{id}`, `POST /documents/{id}/reprocess` |
| Chat | `POST /chat/messages`, `GET /chat/sessions`, `GET /chat/sessions/{id}/messages`, `DELETE /chat/sessions/{id}`, `GET /model-configurations` |
| Datasets | `/datasets` (tạo, liệt kê, chi tiết), `/datasets/{id}/versions`, `/dataset-versions/{id}/review`, `/dataset-versions/{id}/test-cases` (+ import), `/test-cases/{id}` |
| Evaluations | `POST /evaluations`, `GET /evaluations`, `GET /evaluations/{id}`, `GET /evaluations/{id}/results`, `GET /evaluations/{id}/report`, `/model-configurations`, `GET /datasets` và `/versions` (để chọn) |
| Security | `GET /model-configurations`, `GET /security/test-cases`, `POST /security/runs`, `GET /security/runs`, `GET /security/runs/{id}`, `/results`, `/report` |
| Benchmarks | `POST /benchmarks`, `GET /benchmarks`, `GET /benchmarks/{id}`, `GET /benchmarks/{id}/report` |

Mọi trang xử lý ba trạng thái: đang tải, lỗi (hiển thị `error.message`), và thành công. Trang có tác vụ dài (Documents, Evaluations, Security, Benchmarks) hiển thị `status` và tiến độ bằng cách poll endpoint chi tiết.

## 12. Điều kiện kiểm chứng

- Mỗi endpoint trong Master Prompt mục 7 có mặt trong tài liệu này.
- Mỗi trang frontend trong repo (`pages/`) có dòng ở mục 11 và mọi endpoint nó gọi có định nghĩa ở trên.
- Tên trường khớp với cột trong `07_database.md`.

## 13. Quyết định đã chọn và lý do

1. **Thêm nhóm `/model-configurations`** (Master Prompt không liệt kê). Evaluation, Security và Benchmark đều cần chọn một cấu hình; nếu không có endpoint, frontend phải gửi cả bộ tham số mỗi lần và ta mất khả năng nói "hai run dùng cùng một cấu hình". Cấu hình bất biến nên không có endpoint sửa.
2. **Sửa version đã duyệt trả `409`, không phải `403`.** `403` nghĩa là "bạn không có quyền"; ở đây bạn *có* quyền với dataset, nhưng trạng thái hiện tại không cho phép thao tác. `409 Conflict` mô tả đúng hơn, và frontend có thể hiển thị gợi ý "tạo version mới".
3. **Import test case: từ chối cả file nếu có dòng lỗi.** Dataset là nền của mọi điểm đánh giá, nên một dòng sai lặng lẽ lọt vào còn nguy hiểm hơn việc phải sửa file và import lại. Báo lỗi nêu số dòng và lý do để sửa nhanh. *Giả định yếu:* "người dùng sẽ sửa được file theo thông báo lỗi." Vì vậy thông báo lỗi phải chỉ rõ dòng và trường.
4. **Trả `404` thay vì `403` cho tài nguyên của user khác.** Trả `403` xác nhận rằng tài nguyên *có tồn tại* nhưng thuộc người khác, đó là thông tin rò rỉ (information disclosure). `404` che giấu sự tồn tại.
5. **Đăng nhập sai trả thông báo chung.** Không nói riêng "email không tồn tại" hay "sai mật khẩu" để tránh cho kẻ tấn công dò email có đăng ký hay chưa (user enumeration). *Giả định yếu:* thông báo chung vẫn có thể bị dò bằng thời gian phản hồi; ghi nhận, xử lý ở mức chấp nhận được cho MVP.

## 14. Giải thích khái niệm cho người mới

- **REST và HTTP status code**: mỗi tài nguyên (document, run) có một địa chỉ, và hành động được thể hiện bằng phương thức: `GET` đọc, `POST` tạo hoặc kích hoạt, `PUT` thay thế, `DELETE` xóa. Mã trạng thái cho biết kết quả: 2xx thành công, 4xx lỗi do client, 5xx lỗi phía server.
- **`202 Accepted`**: "đã nhận, đang xử lý". Dùng cho tác vụ dài; kết quả cuối cùng lấy bằng cách hỏi lại (polling) endpoint chi tiết.
- **JWT (JSON Web Token)**: chuỗi do server ký, chứa danh tính user và thời hạn. Client gửi kèm mỗi request; server kiểm tra chữ ký mà không cần tra DB phiên đăng nhập. Hạn chế: không thu hồi tức thời trước khi hết hạn, nên thời hạn phải đủ ngắn.
- **Authentication và Authorization**: authentication trả lời "bạn là ai"; authorization trả lời "bạn có được làm việc này với tài nguyên này không". Dự án làm cả hai: JWT cho cái đầu, kiểm tra `user_id` sở hữu cho cái sau.
- **Schema (Pydantic)**: mô tả hình dạng dữ liệu vào ra và kiểm tra tự động; dữ liệu sai bị từ chối với `422` trước khi vào logic nghiệp vụ. Đây là nơi chặn đầu vào xấu rẻ nhất.
- **CORS**: trình duyệt chặn trang web gọi API ở nguồn (origin) khác trừ khi server cho phép. Vì frontend và backend chạy ở cổng khác nhau, backend phải cấu hình danh sách origin được phép; đừng đặt `*` cho API có đăng nhập.
- **Pagination**: trả dữ liệu theo trang (`limit`, `offset`) để danh sách lớn không làm chậm hay làm nghẽn bộ nhớ.
