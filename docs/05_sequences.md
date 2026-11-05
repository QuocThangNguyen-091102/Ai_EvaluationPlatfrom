# 05. Sơ đồ Sequence (M1-T05)

Trạng thái: bản nháp chờ duyệt. Khớp với mục 5.1 đến 5.4 của Master Prompt. Số lần retry và timeout là cấu hình, không cố định trong tài liệu.

## Điểm tái sử dụng RAG Pipeline

`RAG Pipeline` (`ai_engine/pipeline/rag_pipeline.py`) là điểm dùng chung. Ba luồng dưới đây (RAG, Evaluation, Security) đều gọi **cùng một hàm** của pipeline; luồng Benchmark gọi qua Evaluation Runner nên cũng dùng lại. Khác biệt chỉ nằm ở caller và nơi lưu kết quả:

| Caller | Đầu vào RAGConfig từ | Kết quả lưu vào |
|--------|----------------------|-----------------|
| ChatService | Cấu hình mặc định hoặc user chọn | ChatMessage, RetrievedContext |
| Evaluation Runner | Cấu hình của EvaluationRun | EvaluationResult, MetricResult |
| Benchmark Runner | Cấu hình từng nhánh benchmark, qua Evaluation Runner | EvaluationRun con của BenchmarkRun |
| Security Runner | Cấu hình của SecurityTestRun | SecurityTestResult |

## Ghi chú về lưu kết quả của runner

Evaluation Runner và Security Runner **không gọi Repository** (quy tắc phụ thuộc ở `09_repo_manifest.md` mục 4). Service truyền vào một callback; runner gọi callback để báo lỗi, kết quả từng case và tiến độ, Service lưu qua Repository. Trong các sơ đồ dưới, mũi tên `RUN-->>SVC: Callback` thể hiện điều này.

## 1. Document Ingestion (mục 5.1)

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend
    participant API as Documents Router
    participant SVC as DocumentService
    participant FS as File storage
    participant ING as Ingestion (parser, cleaner, chunker)
    participant EMB as Embedding adapter
    participant EP as Embedding Provider
    participant REPO as Repository
    participant DB as PostgreSQL + pgvector

    U->>FE: Chọn file và upload
    FE->>API: POST /documents (file, token)
    API->>API: Xác thực, validate loại file và dung lượng
    API->>SVC: upload(user_id, file)
    SVC->>SVC: Tính hash nội dung
    SVC->>REPO: Tìm document cùng user_id và hash
    alt Đã có document trùng
        REPO-->>SVC: document hiện có
        SVC-->>API: Lỗi xung đột kèm id document hiện có
        API-->>FE: 409 Conflict
    else Chưa có
        SVC->>FS: Lưu file gốc
        SVC->>REPO: Tạo Document (status = uploaded)
        REPO->>DB: INSERT
        SVC-->>API: Document (uploaded)
        API-->>FE: 202 Accepted
        Note over SVC,ING: Xử lý tiếp chạy nền, request đã trả về
        SVC->>REPO: status = processing
        SVC->>ING: Parse file, làm sạch, chunk
        alt Parse lỗi (file hỏng, không đọc được)
            ING-->>SVC: Lỗi
            SVC->>REPO: status = failed, ghi lý do
        else Parse thành công
            ING-->>SVC: Danh sách chunk kèm metadata
            loop Từng lô chunk
                SVC->>EMB: embed(chunks)
                EMB->>EP: Gọi API
                alt Timeout hoặc rate limit
                    EMB->>EMB: Retry có giới hạn (backoff)
                end
                EP-->>EMB: Vector
            end
            alt Embedding thất bại sau khi hết retry
                SVC->>REPO: status = failed, ghi lý do (chưa có chunk nào được ghi)
            else Thành công
                SVC->>REPO: Lưu chunk và vector trong một transaction
                REPO->>DB: INSERT chunks
                SVC->>REPO: status = ready
            end
        end
    end
    FE->>API: GET /documents/{id} (poll trạng thái)
    API-->>FE: status (processing, ready, failed)
```

### Hành vi khác trong luồng ingestion

| Tình huống | Hành vi |
|------------|-----------------|
| **Upload trùng** | So hash nội dung trong cùng user. Trùng thì từ chối với 409 và trả id document đã có. Hai user khác nhau upload cùng file thì mỗi người có bản riêng (cô lập dữ liệu). |
| **Retry** | Chỉ retry lỗi tạm thời (timeout, rate limit, lỗi 5xx của provider), số lần và thời gian chờ cấu hình được. Không retry lỗi do dữ liệu (file hỏng). |
| **Xóa document** | Xóa chunk (cascade), xóa file gốc, xóa bản ghi Document. Nếu xóa file lỗi thì ghi log và không để lại chunk mồ côi. Các bản ghi lịch sử (ChatMessage, RetrievedContext) cần tham chiếu an toàn; quy tắc cascade chi tiết ở `07_database.md` mục 6. |
| **Reprocess** | Chuyển status về processing, xóa chunk cũ và ghi chunk mới trong cùng một transaction để không tạo chunk trùng. Thất bại thì giữ trạng thái failed kèm lý do. |
| **Tiến trình bị gián đoạn** (backend khởi động lại giữa chừng) | Document kẹt ở processing. Cần cơ chế phát hiện (ví dụ quá hạn thì đánh dấu failed để user reprocess). Ghi vào rủi ro, chốt ở M3. |

## 2. RAG: hỏi đáp (mục 5.2)

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend
    participant API as Chat Router
    participant SVC as ChatService
    participant PIPE as RAG Pipeline (dùng chung)
    participant EMB as Embedding adapter
    participant RET as Retriever
    participant DB as PostgreSQL + pgvector
    participant GEN as LLM client
    participant LP as LLM Provider
    participant REPO as Repository

    U->>FE: Nhập câu hỏi
    FE->>API: POST /chat/messages (câu hỏi, session, token)
    API->>API: Xác thực user
    API->>SVC: ask(user_id, session_id, question)
    SVC->>PIPE: run(question, user_id, RAGConfig)
    PIPE->>EMB: embed(question)
    EMB-->>PIPE: Vector câu hỏi
    PIPE->>RET: search(vector, user_id, Top-K, filter)
    RET->>DB: Vector search + điều kiện user_id và document được phép
    DB-->>RET: Chunk kèm điểm
    RET-->>PIPE: Danh sách chunk
    alt Không có chunk đủ liên quan
        PIPE-->>SVC: Câu trả lời "không đủ thông tin", contexts rỗng hoặc yếu
    else Có context
        PIPE->>PIPE: Dựng context và prompt (có version)
        PIPE->>GEN: generate(prompt, temperature)
        GEN->>LP: Gọi API
        alt Timeout hoặc rate limit
            GEN->>GEN: Retry có giới hạn
        end
        LP-->>GEN: Câu trả lời, token usage
        GEN-->>PIPE: Answer
        PIPE-->>SVC: Answer, citations, contexts kèm điểm, latency, token, chi phí ước tính
    end
    SVC->>REPO: Lưu ChatMessage, RetrievedContext, cấu hình, latency, token
    REPO->>DB: INSERT
    SVC-->>API: Kết quả
    API-->>FE: Answer kèm citations
```

Lọc quyền diễn ra **trong câu truy vấn vector** (điều kiện `user_id` và document được phép), không chỉ ở API, nên một câu hỏi cố tình nhắm vào dữ liệu của user khác cũng không nhận được chunk của họ.

Lỗi provider kéo dài (hết retry): pipeline trả lỗi rõ cho caller; ChatService trả lỗi chuẩn cho frontend, không bịa câu trả lời.

## 3. Evaluation (mục 5.3)

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend
    participant API as Evaluations Router
    participant SVC as EvaluationService
    participant RUN as Evaluation Runner
    participant DS as Dataset (version đã duyệt)
    participant PIPE as RAG Pipeline (dùng chung)
    participant MET as Metrics
    participant JUDGE as LLM Judge
    participant REPO as Repository

    U->>FE: Chọn dataset version và cấu hình, bấm chạy
    FE->>API: POST /evaluations (dataset_version_id, config)
    API->>SVC: create_run(user_id, dataset_version_id, model_configuration_id, judge_model, judge_prompt_version)
    SVC->>REPO: Tạo EvaluationRun (status = pending, lưu toàn bộ metadata cấu hình)
    SVC-->>API: run_id
    API-->>FE: 202 Accepted
    Note over SVC,RUN: Chạy nền, frontend poll tiến độ

    SVC->>RUN: execute(run_id, callback lưu kết quả)
    SVC->>REPO: status = running
    RUN->>DS: Nạp test case của version
    loop Từng test case
        RUN->>PIPE: run(question, user_id, RAGConfig)
        alt Pipeline hoặc provider lỗi
            PIPE-->>RUN: Lỗi
            RUN-->>SVC: Callback (Service lưu qua Repository): Lưu lỗi của case này, tiếp tục case sau
        else Thành công
            PIPE-->>RUN: Answer, retrieved contexts, latency, token
            RUN->>MET: Retrieval metrics (so với reference contexts)
            RUN->>JUDGE: Generation metrics (cần LLM judge)
            alt Judge lỗi
                JUDGE-->>RUN: Lỗi
                RUN-->>SVC: Callback (Service lưu qua Repository): Đánh dấu metric không tính được, không điền số giả
            else Thành công
                JUDGE-->>RUN: Điểm kèm lý do
            end
            RUN-->>SVC: Callback (Service lưu qua Repository): Lưu EvaluationResult và MetricResult của case
        end
        RUN-->>SVC: Callback (Service lưu qua Repository): Cập nhật tiến độ
    end
    RUN-->>SVC: Callback (Service lưu qua Repository): Tổng hợp điểm, status = completed
    FE->>API: GET /evaluations/{id} và /results (poll)
    API-->>FE: Tiến độ, điểm tổng hợp, từng case
```

Bản ghi `EvaluationRun` lưu: dataset version, model và version, embedding model, prompt version, chunk size, overlap, Top-K, temperature, framework version, model và prompt của judge, timestamp. Run chỉ được đánh dấu `completed` sau khi mọi case đã có kết quả hoặc lỗi được ghi.

Nếu backend khởi động lại giữa lúc chạy, run kẹt ở `running`; cần cơ chế đánh dấu lại (chốt ở M6, cùng loại với trường hợp ingestion).

## 4. Security Testing (mục 5.4)

```mermaid
sequenceDiagram
    actor U as User (Security Reviewer)
    participant FE as Frontend
    participant API as Security Router
    participant SVC as SecurityService
    participant RUN as Security Runner
    participant TC as Test cases (YAML)
    participant PIPE as RAG Pipeline (dùng chung)
    participant EVAL as Result Evaluator
    participant JUDGE as LLM Judge (tùy chọn)
    participant REPO as Repository

    U->>FE: Chọn nhóm test và bắt đầu
    FE->>API: POST /security/runs
    API->>SVC: start_run(user_id, model_configuration_id, categories)
    SVC->>REPO: Tạo SecurityTestRun (status = pending)
    SVC-->>API: run_id
    API-->>FE: 202 Accepted

    SVC->>RUN: execute(run_id, callback lưu kết quả)
    SVC->>REPO: status = running
    RUN->>TC: Nạp và validate test case đã duyệt
    Note over RUN: Chuẩn bị môi trường thử nghiệm: tài khoản và tài liệu giả, canary token
    loop Từng test case
        RUN->>PIPE: run(input của test case, user_id (có thể là user thứ hai), RAGConfig)
        alt Pipeline lỗi
            PIPE-->>RUN: Lỗi
            RUN-->>SVC: Callback (Service lưu qua Repository): Lưu lỗi của case, tiếp tục
        else Có phản hồi
            PIPE-->>RUN: Answer, retrieved contexts
            RUN->>EVAL: So hành vi thực tế với hành vi mong đợi
            EVAL->>EVAL: Luật xác định (ví dụ phát hiện canary token trong câu trả lời)
            opt Cần đánh giá ngữ nghĩa
                EVAL->>JUDGE: Hỏi judge
                JUDGE-->>EVAL: Phán định
            end
            EVAL-->>RUN: pass hoặc fail, severity, evidence
            RUN-->>SVC: Callback (Service lưu qua Repository): Lưu SecurityTestResult kèm evidence và khuyến nghị
        end
    end
    RUN-->>SVC: Callback (Service lưu qua Repository): Tổng hợp, status = completed
    FE->>API: GET /security/runs/{id}
    API-->>FE: Kết quả, evidence, giới hạn độ phủ
```

Phạm vi: chỉ chạy trên ứng dụng RAG do dự án kiểm soát, với dữ liệu giả và canary token. Test Access Control dùng hai user khác nhau để chứng minh cô lập. Báo cáo cuối nêu rõ nhóm hoặc kịch bản chưa kiểm tra và không kết luận "an toàn tuyệt đối".

## 5. Đối chiếu với Master Prompt

| Mục Master Prompt | Sơ đồ | Điểm khớp |
|-------------------|-------|-----------|
| 5.1 Document ingestion | Mục 1 | Xác thực, validate, lưu file gốc, parser, preprocessing, chunker, embedding, lưu chunk và vector, trả status; có retry, lỗi, trùng, xóa, reprocess |
| 5.2 Question answering | Mục 2 | Xác thực, kiểm tra quyền, embed câu hỏi, retrieval có filter, dựng context và prompt, gọi LLM, citations, ghi log, xử lý thiếu bằng chứng |
| 5.3 Evaluation | Mục 3 | Run gắn dataset version và cấu hình, gọi cùng pipeline với chat, lưu answer và contexts, tính metric, tổng hợp, giữ lỗi từng case |
| 5.4 Security testing | Mục 4 | Nạp test case đã duyệt, chạy trên ứng dụng kiểm soát, so sánh mong đợi và thực tế, pass/fail và severity, lưu evidence, nêu giới hạn |
