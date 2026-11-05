# 09. Cây thư mục repo và File manifest (M1-T09)

Trạng thái: bản nháp chờ duyệt. Đã điều chỉnh bản đề xuất của Master Prompt theo MVP (mục 2).

## 1. Trạng thái và quy ước

- **Created**: file đã có trong repo (hiện đều rỗng, chưa có nội dung).
- **Planned**: file chưa tồn tại, sẽ được tạo ở milestone ghi trong cột cuối. **Không tạo trước.**
- Các trạng thái còn lại: Implemented, Tested, Needs Revision (dùng từ M2 trở đi).
- Cột **Dùng bởi** cho biết ai import hoặc gọi file này. Cột **Milestone** là lúc file được hiện thực.
- Tên file theo quy ước ở `CLAUDE.md` mục 8.

## 2. Điều chỉnh so với đề xuất của Master Prompt

### Đã xóa (file rỗng, đầu cơ hoặc trùng lặp)

| File | Lý do |
|------|-------|
| `ai_engine/chunking/base_chunker.py`, `recursive_chunker.py` | MVP chỉ có một chiến lược chunk (`fixed_size_chunker.py`). Chunker khác là Deferred; thêm interface khi thật sự có chiến lược thứ hai |
| `configs/app.yaml` | Trùng với biến môi trường (`config.py`); không có cấu hình nào cần nằm ở đây |
| `scripts/init_db.sh` | Migration chạy bằng `alembic upgrade head` (xem `06_deployment_tech.md`) |
| `docs/diagrams/*.mmd` (9 file) | Sơ đồ Mermaid nằm ngay trong các tài liệu `04`, `05`, `06`, `07`; tránh hai nguồn sự thật |
| `ai_engine/adapters/` (đề xuất gốc) | Adapter provider đã nằm trong `embeddings/` và `generation/`; không cần thư mục riêng |

### Sẽ thêm khi tới milestone (Planned, chưa tạo)

| File | Lý do |
|------|-------|
| `backend/app/api/routes/model_configs.py`, `schemas/model_config.py`, `repositories/model_config_repository.py`, `services/model_config_service.py` | Nhóm endpoint `/model-configurations` (xem `08_api_contracts.md`) |
| `backend/app/models/retrieved_context.py` | Bảng dùng chung cho chat, evaluation, security (xem `07_database.md`) |
| `backend/app/core/file_storage.py` | Lưu, xóa file gốc (một chỗ duy nhất đụng tới đĩa) |
| `ai_engine/pipeline/rag_config.py`, `rag_result.py` | Kiểu dữ liệu vào và ra của pipeline, để pipeline gọi được ngoài FastAPI |
| `ai_engine/generation/cost_estimator.py` | Ước tính chi phí từ token, đọc bảng giá trong `configs/models.yaml` |
| `ai_engine/provider_retry.py` | Retry có giới hạn và backoff dùng chung cho embedding và LLM |
| `evaluation/evaluators/judge_prompts.py` | Prompt judge có version tách khỏi logic gọi judge |
| `security/test_case_loader.py` | Nạp và validate test case YAML |
| `frontend/src/services/api/modelConfigApi.js`, `frontend/src/components/ProtectedRoute.jsx` | Gọi API cấu hình; chặn route khi chưa đăng nhập |
| File test (`test_*.py`) | Tạo cùng lúc với code của từng task |

## 3. Cây thư mục chốt cho MVP

Chú thích: `[P]` là file Planned (chưa tạo). Không đánh dấu nghĩa là Created (rỗng).

```
ai-evaluation-platform/
├── CLAUDE.md
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── configs/
│   ├── models.yaml                  # danh sách model được hỗ trợ, bảng giá (kèm thời điểm)
│   └── rag_default.yaml             # cấu hình RAG mặc định
├── scripts/
│   └── seed_demo.py                 # dữ liệu demo cho kịch bản trình bày
├── docs/
│   ├── 01_feasibility.md ... 10_test_risk_learning.md
│   ├── progress_log.md
│   └── session_notes.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── dependencies.py
│   │   │   └── routes/ (health, auth, documents, chat, datasets, evaluations, security_tests, benchmarks, model_configs [P])
│   │   ├── core/ (config, security, logging, exceptions, file_storage [P])
│   │   ├── database/ (session, base, migrations/)
│   │   ├── models/ (user, document, document_chunk, chat, retrieved_context [P], dataset, evaluation, security_test, model_config, benchmark, report)
│   │   ├── schemas/ (auth, document, chat, dataset, evaluation, security_test, benchmark, model_config [P])
│   │   ├── repositories/ (user, document, chunk, chat, dataset, evaluation, security, benchmark, model_config [P])
│   │   └── services/ (auth, document, chat, dataset, evaluation, security, benchmark, report, model_config [P])
│   └── tests/ (conftest.py, unit/, integration/, e2e/)
├── ai_engine/
│   ├── provider_retry.py            [P]
│   ├── ingestion/ (pdf_parser, docx_parser, txt_parser, text_cleaner, ingestion_pipeline)
│   ├── chunking/ (fixed_size_chunker)
│   ├── embeddings/ (base_embedder, local_embedder)
│   ├── retrieval/ (vector_retriever, metadata_filters)
│   ├── generation/ (base_llm_client, openai_llm_client, prompt_templates, cost_estimator [P])
│   └── pipeline/ (rag_pipeline, context_builder, rag_config [P], rag_result [P])
├── evaluation/
│   ├── datasets/dataset_loader.py
│   ├── metrics/retrieval/ (precision_at_k, recall_at_k, mrr, ndcg_at_k)
│   ├── metrics/generation/ (faithfulness, answer_relevancy, context_precision, context_recall)
│   ├── evaluators/ (llm_judge, judge_prompts [P])
│   ├── runners/evaluation_runner.py
│   ├── benchmarks/benchmark_runner.py
│   └── reports/report_builder.py
├── security/
│   ├── test_case_loader.py          [P]
│   ├── test_cases/ (prompt_injection, jailbreak, data_leakage, access_control, malicious_documents .yaml)
│   ├── runners/security_runner.py
│   ├── evaluators/security_result_evaluator.py
│   └── reports/security_report_builder.py
└── frontend/
    ├── Dockerfile, package.json, index.html, vite.config.js
    ├── public/
    └── src/
        ├── main.jsx, App.jsx
        ├── pages/ (Login, Dashboard, Documents, Chat, Datasets, Evaluations, Security, Benchmarks)
        ├── layouts/MainLayout.jsx
        ├── contexts/AuthContext.jsx
        ├── hooks/useAuth.js
        ├── components/ (ProtectedRoute.jsx [P], thêm khi cần)
        └── services/api/ (httpClient, authApi, documentApi, chatApi, datasetApi, evaluationApi, securityApi, benchmarkApi, modelConfigApi [P])
```

## 4. Quy tắc phụ thuộc giữa các thư mục

```
frontend  ->  (chỉ gọi) REST API của backend
backend/api  ->  backend/services  ->  backend/repositories  ->  backend/models
backend/services  ->  ai_engine, evaluation, security
evaluation, security  ->  ai_engine/pipeline
security  ->  evaluation/evaluators (chỉ llm_judge.py)
ai_engine/retrieval  ->  nhận DB session từ caller (ngoại lệ có chủ đích, xem 04 mục 5)
runner (evaluation, security)  ->  không truy cập DB; Service truyền callback lưu kết quả
ai_engine  ->  (không import backend, không import FastAPI)
evaluation, security  ->  (không import backend/app; nhận dữ liệu qua tham số)
```

Lý do: `ai_engine` gọi được từ script độc lập (tiêu chí của M4-T04) và dùng chung cho mọi luồng; `evaluation`, `security` không phụ thuộc cách backend lưu dữ liệu nên kiểm thử đơn vị dễ.

Phân biệt các lớp: **Router** nhận request và validate; **Schema** là hình dạng dữ liệu vào ra API; **Model** là bảng DB (ORM); **Repository** là nơi duy nhất truy cập DB; **Service** là use case điều phối; **AI Engine** là logic miền AI, không biết tới HTTP hay DB.

## 5. Manifest chi tiết

### 5.1 Gốc repo, cấu hình, scripts, docs

| Đường dẫn | Trách nhiệm | Phụ thuộc | Dùng bởi | Input | Output | Trạng thái | Milestone |
|-----------|-------------|-----------|----------|-------|--------|------------|-----------|
| `CLAUDE.md` | Ràng buộc làm việc của dự án | Không | Claude Code | | | Implemented | M1 |
| `README.md` | Hướng dẫn cài, chạy, test, kiến trúc, giới hạn | Mọi phần | Người đọc repo | | | Implemented | M2, hoàn thiện M9 |
| `docker-compose.yml` | Định nghĩa service db, backend, frontend, volume, healthcheck | `backend/Dockerfile`, `frontend/Dockerfile`, `.env` | Dev, demo | `.env` | Stack chạy được | Implemented | M2 |
| `.env.example` | Mẫu biến môi trường, không chứa secret | Không | Dev | | | Implemented | M2 |
| `.gitignore` | Loại `.env`, cache, file upload khỏi Git | Không | Git | | | Implemented | M2 |
| `configs/models.yaml` | Model được hỗ trợ, bảng giá kèm thời điểm lấy | Không | `cost_estimator.py`, `model_config_service.py` | | Danh sách model, giá | Created | M3 |
| `configs/rag_default.yaml` | Giá trị RAG mặc định (chunk size, overlap, Top-K, temperature, prompt version) | Không | `core/config.py`, `model_config_service.py` | | Cấu hình mặc định | Created | M3 |
| `scripts/seed_demo.py` | Tạo dữ liệu demo cho kịch bản trình bày | Backend, tài liệu mẫu | Dev | | Dữ liệu mẫu trong DB | Created | M9 |
| `docs/01_feasibility.md` … `docs/10_test_risk_learning.md` | Tài liệu thiết kế M1 | Không | Mọi người | | | Implemented (bản nháp chờ duyệt) | M1 |
| `docs/11_free_deployment.md` | Kế hoạch triển khai miễn phí lên internet (Vercel cho giao diện, máy chủ container cho backend) | Không | Mọi người | | | Implemented (bản nháp chờ duyệt) | M1, thực hiện M9-T04 |
| `docs/progress_log.md` | Nhật ký kết quả từng task | Không | Người dùng, Claude | | | Implemented | M1 |
| `docs/session_notes.md` | Ghi chú cuối phiên | Không | Claude | | | Implemented | M1 |
| `docs/baseline_manual.md` | Bảng kết quả hỏi đáp thủ công (khoảng 20 câu) làm điểm tham chiếu | Không | Người dùng | | | Planned | M4 |
| `docs/corpus_sources.md` | Nguồn và quyền sử dụng tài liệu corpus đánh giá | Không | Người dùng | | | Planned | M5 |
| `docs/metrics_notes.md` | Ghi chú cách tính metric, thiên lệch của judge | Không | Người dùng | | | Planned | M6 |
| `docs/error_analysis.md` | Phân loại lỗi và mức đồng thuận judge và người | Không | Người dùng | | | Planned | M6 |
| `docs/security_scope.md` | Phạm vi, threat model của kiểm thử bảo mật | Không | Người dùng | | | Planned | M7 |
| `docs/benchmark_design.md` | Ma trận so sánh cấu hình | Không | Người dùng | | | Planned | M8 |

### 5.2 Backend: lõi và hạ tầng

| Đường dẫn | Trách nhiệm | Phụ thuộc | Dùng bởi | Input | Output | Trạng thái | Milestone |
|-----------|-------------|-----------|----------|-------|--------|------------|-----------|
| `backend/Dockerfile` | Build image backend | `requirements.txt` | `docker-compose.yml` | | Image | Implemented | M2 |
| `backend/requirements.txt` | Danh sách dependency Python | Không | Dockerfile, dev | | | Implemented | M2 |
| `backend/alembic.ini` | Cấu hình Alembic | `database/migrations/` | Alembic | | | Implemented | M2 |
| `backend/app/main.py` | Khởi tạo FastAPI, đăng ký router, middleware lỗi và CORS | `api/routes/*`, `core/*` | uvicorn | | App FastAPI | Implemented | M2 |
| `backend/app/core/config.py` | Đọc cấu hình từ biến môi trường | `configs/*.yaml` | Mọi module backend | Biến môi trường | Đối tượng settings | Implemented | M2 |
| `backend/app/core/security.py` | Hash mật khẩu, tạo và kiểm tra JWT | `config.py` | `auth_service.py`, `api/dependencies.py` | Mật khẩu, token | Hash, token, claims | Tested | M3 |
| `backend/app/core/logging.py` | Cấu hình log, không ghi dữ liệu nhạy cảm | `config.py` | `main.py` | | Logger | Implemented | M2 |
| `backend/app/core/exceptions.py` | Lỗi nghiệp vụ và bộ chuyển thành JSON lỗi thống nhất | Không | Service, `main.py` | | Phản hồi lỗi chuẩn | Tested | M2 |
| `backend/app/core/file_storage.py` | Lưu, đọc, xóa file gốc trong volume | `config.py` | `document_service.py` | File, đường dẫn | Đường dẫn lưu | Tested | M3 |
| `backend/Dockerfile.dockerignore` | Loại `.venv`, test, giao diện, tài liệu khỏi build context (context là thư mục gốc repo) | Không | Docker build | | | Implemented | M2 |
| `backend/requirements-dev.txt` | Dependency chỉ dùng khi phát triển (pytest, httpx), tách khỏi image chạy thật | `requirements.txt` | Dev | | | Implemented | M2 |
| `backend/pytest.ini` | Cấu hình pytest, marker `integration` | Không | pytest | | | Implemented | M2 |
| `backend/tests/conftest.py` | Fixture `client`, bảo đảm có `DATABASE_URL` khi chạy unit test | `app.main` | Mọi test | | | Tested | M2 |
| `backend/tests/unit/test_health.py`, `test_error_handling.py` | Unit test `/health` và bộ xử lý lỗi chuẩn | `app.main`, `core/exceptions.py` | pytest | | | Tested | M2 |
| `backend/tests/integration/test_health_database.py` | Test `/health` với PostgreSQL thật | DB đang chạy | pytest | | | Tested | M2 |
| `backend/app/database/migrations/versions/0002_create_users_documents_chunks.py` | Tạo bảng `users`, `documents`, `document_chunks` (vector 384 chiều, khóa ngoại kép, chỉ mục) | `models/*`, `pgvector` | Alembic | | Schema DB | Tested | M3 |
| `backend/tests/integration/test_ingestion_schema.py` | Kiểm tra bảng, số chiều vector, ràng buộc, cascade, truy vấn khoảng cách | DB đang chạy | pytest | | | Tested | M3 |
| `backend/tests/unit/test_security.py`, `test_auth_schemas.py` | Unit test băm mật khẩu, JWT (hết hạn, sai khóa, alg none, thiếu claim), schema đăng ký | `core/security.py`, `schemas/auth.py` | pytest | | | Tested | M3 |
| `backend/tests/integration/test_auth_api.py` | Test API đăng ký, đăng nhập, `/auth/me` với PostgreSQL thật (rollback cuối mỗi test) | DB đang chạy | pytest | | | Tested | M3 |
| `backend/app/core/file_validation.py` | Nhận diện PDF, DOCX, TXT (UTF-8) bằng nội dung, làm sạch tên hiển thị | Không | `services/document_service.py` | Tên file, nội dung | Loại file hợp lệ hoặc lỗi | Tested | M3 |
| `backend/tests/unit/test_file_validation.py` | Unit test nhận diện loại file và làm sạch tên | `core/file_validation.py` | pytest | | | Tested | M3 |
| `backend/tests/integration/test_document_upload_api.py` | Test API upload với PostgreSQL thật và thư mục tạm | DB đang chạy | pytest | | | Tested | M3 |
| `ai_engine/ingestion/parsed_document.py` | Kiểu dữ liệu chung `ParsedDocument`, `ParsedPage`, `ParsingError` | Không | Parsers, cleaner, chunker | | | Tested | M3 |
| `backend/tests/unit/test_parsers.py`, `test_text_cleaner.py`, `test_chunker.py`, `test_local_embedder.py` | Unit test parser, làm sạch, chunker, adapter embedding (model giả; 5 test model thật chạy khi `RUN_MODEL_TESTS=1`) | `ai_engine/*` | pytest | | | Tested | M3 |
| `backend/tests/fixtures/vi_two_pages.pdf` | PDF mẫu tiếng Việt có dấu, 2 trang, để test parser | Không | `test_parsers.py`, `test_chunker.py` | | | Implemented | M3 |
| `backend/tests/integration/test_document_management_api.py` | Test API danh sách, chi tiết, xóa tài liệu (có cô lập user, phân trang) | DB đang chạy | pytest | | | Tested | M3 |
| `backend/app/database/session.py` | Tạo engine và session DB, dependency lấy session | `config.py` | Repository, `api/dependencies.py` | `DATABASE_URL` | Session | Implemented | M2 |
| `backend/app/database/base.py` | Lớp Base của ORM | Không | `models/*` | | | Implemented | M2 |
| `backend/app/database/migrations/` | Lịch sử migration Alembic | `models/*` | Alembic | | Schema DB | Implemented (migration `0001` bật extension vector) | M2 trở đi |
| `backend/app/database/migrations/env.py`, `script.py.mako`, `versions/` | Cấu hình chạy Alembic và các file migration | `models/*`, `core/config.py` | Alembic | `DATABASE_URL` | Schema DB | Implemented | M2 |
| `backend/app/api/dependencies.py` | Dependency xác thực, lấy current user và session | `core/security.py`, `database/session.py` | Mọi router | Request | `current_user`, session | Tested | M3 |

### 5.3 Backend: routes

Tất cả route: phụ thuộc vào service tương ứng và schema tương ứng; được `main.py` đăng ký; input là request HTTP, output là response theo `08_api_contracts.md`.

| Đường dẫn | Trách nhiệm | Service dùng | Trạng thái | Milestone |
|-----------|-------------|--------------|------------|-----------|
| `backend/app/api/routes/health.py` | `GET /health` | (kiểm tra DB trực tiếp qua session) | Tested | M2 |
| `backend/app/api/routes/auth.py` | Register, login, me | `auth_service.py` | Tested | M3 |
| `backend/app/api/routes/documents.py` | Upload, list, detail, delete, reprocess | `document_service.py` | Created (upload: Tested) | M3 |
| `backend/app/api/routes/chat.py` | Hỏi đáp, session, message | `chat_service.py` | Created | M4 |
| `backend/app/api/routes/model_configs.py` | Cấu hình model | `model_config_service.py` | Planned | M4 |
| `backend/app/api/routes/datasets.py` | Dataset, version, test case, import | `dataset_service.py` | Created | M5 |
| `backend/app/api/routes/evaluations.py` | Run, kết quả, báo cáo | `evaluation_service.py`, `report_service.py` | Created | M6 |
| `backend/app/api/routes/security_tests.py` | Run bảo mật, kết quả, báo cáo | `security_service.py`, `report_service.py` | Created | M7 |
| `backend/app/api/routes/benchmarks.py` | Benchmark, báo cáo | `benchmark_service.py`, `report_service.py` | Created | M8 |
| `backend/app/api/routes/__init__.py` | Đánh dấu package | | Created | M2 |

### 5.4 Backend: models, schemas, repositories, services

Mỗi hàng là một nhóm cùng tên miền. Với `models`: định nghĩa bảng theo `07_database.md`; `schemas`: hình dạng request và response theo `08_api_contracts.md`; `repositories`: truy cập DB và luôn lọc theo `user_id`; `services`: use case.

| Miền | models | schemas | repositories | services | Trạng thái | Milestone |
|------|--------|---------|--------------|----------|------------|-----------|
| Tài khoản | `user.py` (Tested, M3-T01) | `auth.py` (Tested) | `user_repository.py` (Tested) | `auth_service.py` (Tested) | Created | M3 |
| Tài liệu | `document.py`, `document_chunk.py` (Tested, M3-T01) | `document.py` (Tested) | `document_repository.py` (Tested), `chunk_repository.py` | `document_service.py` (upload: Tested; xóa, reprocess: chưa làm; gọi `ai_engine/ingestion/ingestion_pipeline.py`) | Created | M3 |
| Chat | `chat.py`, `retrieved_context.py` [P] | `chat.py` | `chat_repository.py` | `chat_service.py` (gọi `ai_engine/pipeline/rag_pipeline.py`) | Created (trừ [P]) | M4 |
| Cấu hình model | `model_config.py` | `model_config.py` [P] | `model_config_repository.py` [P] | `model_config_service.py` [P] | Created (trừ [P]) | M4 |
| Dataset | `dataset.py` | `dataset.py` | `dataset_repository.py` | `dataset_service.py` | Created | M5 |
| Evaluation | `evaluation.py` (run, result, metric) | `evaluation.py` | `evaluation_repository.py` | `evaluation_service.py` (gọi `evaluation/runners/evaluation_runner.py`) | Created | M6 |
| Security | `security_test.py` | `security_test.py` | `security_repository.py` | `security_service.py` (gọi `security/runners/security_runner.py`) | Created | M7 |
| Benchmark | `benchmark.py` | `benchmark.py` | `benchmark_repository.py` | `benchmark_service.py` (gọi `evaluation/benchmarks/benchmark_runner.py`) | Created | M8 |
| Báo cáo | `report.py` | (dùng schema của evaluation, security, benchmark) | `report_repository.py` [P] (ghi lịch sử xuất, M6) | `report_service.py` (gọi `evaluation/reports/report_builder.py`, `security/reports/security_report_builder.py`) | Created | M6 đến M8 |

Các `__init__.py` trong `models`, `schemas`, `repositories`, `services` chỉ đánh dấu package và để trống hoặc xuất đối tượng chính (Created, M2 trở đi).

### 5.5 AI Engine

| Đường dẫn | Trách nhiệm | Phụ thuộc | Dùng bởi | Input | Output | Trạng thái | Milestone |
|-----------|-------------|-----------|----------|-------|--------|------------|-----------|
| `ai_engine/provider_retry.py` | Retry có giới hạn và backoff cho lỗi tạm thời của provider mạng (LLM ở M4; model embedding cục bộ không cần) | Không | `openai_llm_client.py`, `llm_judge.py` | Hàm gọi, chính sách retry | Kết quả hoặc lỗi cuối | Planned | M3 |
| `ai_engine/ingestion/pdf_parser.py` | Trích văn bản và số trang từ PDF | Thư viện parse PDF | `ingestion_pipeline.py` | File PDF | Văn bản theo trang | Tested | M3 |
| `ai_engine/ingestion/docx_parser.py` | Trích văn bản từ DOCX | Thư viện parse DOCX | `ingestion_pipeline.py` | File DOCX | Văn bản | Tested | M3 |
| `ai_engine/ingestion/txt_parser.py` | Đọc TXT, xử lý encoding | Không | `ingestion_pipeline.py` | File TXT | Văn bản | Tested | M3 |
| `ai_engine/ingestion/text_cleaner.py` | Chuẩn hóa văn bản | Không | `ingestion_pipeline.py` | Văn bản thô | Văn bản sạch | Tested | M3 |
| `ai_engine/ingestion/ingestion_pipeline.py` | Ghép parse, làm sạch, chunk, embed; trả danh sách chunk kèm vector | Parsers, cleaner, chunker, embedder | `document_service.py` | File, cấu hình chunk | Chunk và vector | Created | M3 |
| `ai_engine/chunking/fixed_size_chunker.py` | Chia chunk theo kích thước và overlap, gắn metadata (trang, vị trí ký tự) | Không | `ingestion_pipeline.py` | Văn bản, chunk size, overlap | Danh sách chunk | Tested | M3 |
| `ai_engine/embeddings/base_embedder.py` | Interface embedding provider | Không | `local_embedder.py`, test (provider giả), pipeline | Danh sách văn bản | Danh sách vector | Tested | M3 |
| `ai_engine/embeddings/local_embedder.py` | Cài interface bằng model chạy cục bộ `intfloat/multilingual-e5-small` (384 chiều); thêm tiền tố `query: ` và `passage: ` (quyết định A3 ở `06_deployment_tech.md`) | `base_embedder.py`, `provider_retry.py` | Ingestion, pipeline | Văn bản | Vector | Tested | M3 |
| `ai_engine/retrieval/vector_retriever.py` | Tìm vector gần nhất kèm điều kiện quyền, trả chunk và điểm | DB (pgvector), `metadata_filters.py` | `rag_pipeline.py` | Vector, `user_id`, Top-K | Chunk kèm điểm | Created | M4 |
| `ai_engine/retrieval/metadata_filters.py` | Dựng điều kiện lọc user và document | Không | `vector_retriever.py` | `user_id`, `document_ids` | Điều kiện lọc | Created | M4 |
| `ai_engine/generation/base_llm_client.py` | Interface LLM provider | Không | `openai_llm_client.py`, test, pipeline | Prompt, tham số | Câu trả lời, token | Created | M4 |
| `ai_engine/generation/openai_llm_client.py` | Cài interface cho provider đã chọn (tên sẽ chốt ở M4 theo LLM provider) | `base_llm_client.py`, `provider_retry.py` | Pipeline, `llm_judge.py` | Prompt | Answer, token usage | Created | M4 |
| `ai_engine/generation/prompt_templates.py` | Prompt hệ thống và prompt hỏi đáp có mã phiên bản | Không | `rag_pipeline.py` | Câu hỏi, context | Prompt | Created | M4 |
| `ai_engine/generation/cost_estimator.py` | Ước tính chi phí từ token và bảng giá | `configs/models.yaml` | `rag_pipeline.py` | Token, model | Chi phí ước tính | Planned | M4 |
| `ai_engine/pipeline/rag_config.py` | Kiểu dữ liệu cấu hình pipeline | Không | Pipeline, service, runner | | `RAGConfig` | Planned | M4 |
| `ai_engine/pipeline/rag_result.py` | Kiểu dữ liệu kết quả pipeline (answer, citations, contexts, metrics) | Không | Pipeline, service, runner | | `RagResult` | Planned | M4 |
| `ai_engine/pipeline/context_builder.py` | Dựng context từ chunk, kiểm soát độ dài | Không | `rag_pipeline.py` | Danh sách chunk | Chuỗi context | Created | M4 |
| `ai_engine/pipeline/rag_pipeline.py` | **RAG pipeline duy nhất**: embed câu hỏi, retrieve, dựng context, gọi LLM, xử lý thiếu bằng chứng | Embedder, retriever, LLM client, context builder, cost estimator | `chat_service.py`, `evaluation_runner.py`, `security_runner.py` | Câu hỏi, `user_id`, `RAGConfig` | `RagResult` | Created | M4 |

### 5.6 Evaluation

| Đường dẫn | Trách nhiệm | Phụ thuộc | Dùng bởi | Input | Output | Trạng thái | Milestone |
|-----------|-------------|-----------|----------|-------|--------|------------|-----------|
| `evaluation/datasets/dataset_loader.py` | Đọc và validate file CSV, JSON test case | Không | `dataset_service.py` | File import | Danh sách test case hợp lệ, lỗi theo dòng | Created | M5 |
| `evaluation/metrics/retrieval/precision_at_k.py` | Precision@K (hàm thuần) | Không | `evaluation_runner.py` | Chunk truy xuất, reference | Giá trị | Created | M6 |
| `evaluation/metrics/retrieval/recall_at_k.py` | Recall@K | Không | `evaluation_runner.py` | như trên | Giá trị | Created | M6 |
| `evaluation/metrics/retrieval/mrr.py` | MRR | Không | `evaluation_runner.py` | như trên | Giá trị | Created | M6 |
| `evaluation/metrics/retrieval/ndcg_at_k.py` | NDCG@K | Không | `evaluation_runner.py` | như trên | Giá trị | Created | M6 |
| `evaluation/metrics/generation/faithfulness.py` | Faithfulness (dựa judge) | `llm_judge.py` | `evaluation_runner.py` | Answer, contexts | Điểm kèm lý do | Created | M6 |
| `evaluation/metrics/generation/answer_relevancy.py` | Answer Relevancy | `llm_judge.py` | `evaluation_runner.py` | Câu hỏi, answer | Điểm | Created | M6 |
| `evaluation/metrics/generation/context_precision.py` | Context Precision | `llm_judge.py` | `evaluation_runner.py` | Contexts, ground truth | Điểm | Created | M6 |
| `evaluation/metrics/generation/context_recall.py` | Context Recall | `llm_judge.py` | `evaluation_runner.py` | Contexts, ground truth | Điểm | Created | M6 |
| `evaluation/evaluators/llm_judge.py` | Gọi LLM làm judge, ghi model và prompt của judge | `base_llm_client.py`, `judge_prompts.py`, `provider_retry.py` | Metric sinh, `security_result_evaluator.py` | Prompt judge | Phán định kèm lý do | Created | M6 |
| `evaluation/evaluators/judge_prompts.py` | Prompt judge có version | Không | `llm_judge.py` | | Prompt | Planned | M6 |
| `evaluation/runners/evaluation_runner.py` | Chạy từng case qua pipeline, tính metric, bắt lỗi theo case | `rag_pipeline.py`, metrics | `evaluation_service.py`, `benchmark_runner.py` | Test cases, `RAGConfig` | Kết quả từng case, tổng hợp | Created | M6 |
| `evaluation/benchmarks/benchmark_runner.py` | Chạy nhiều cấu hình qua runner, giữ điều kiện đồng nhất | `evaluation_runner.py` | `benchmark_service.py` | Dataset version, danh sách cấu hình | Các run con | Created | M8 |
| `evaluation/reports/report_builder.py` | Dựng CSV cho evaluation và benchmark | Dữ liệu run | `report_service.py` | Dữ liệu run | File CSV | Created | M6, mở rộng M8 |

### 5.7 Security

| Đường dẫn | Trách nhiệm | Phụ thuộc | Dùng bởi | Input | Output | Trạng thái | Milestone |
|-----------|-------------|-----------|----------|-------|--------|------------|-----------|
| `security/test_case_loader.py` | Nạp và validate test case YAML | Không | `security_service.py`, `security_runner.py` | File YAML | Test case hợp lệ | Planned | M7 |
| `security/test_cases/prompt_injection.yaml` | Test case nhóm Prompt Injection | Không | Loader | | | Created | M7 |
| `security/test_cases/jailbreak.yaml` | Test case nhóm Jailbreak | Không | Loader | | | Created | M7 |
| `security/test_cases/data_leakage.yaml` | Test case nhóm Data Leakage (canary token) | Không | Loader | | | Created | M7 |
| `security/test_cases/access_control.yaml` | Test case nhóm Access Control (hai user) | Không | Loader | | | Created | M7 |
| `security/test_cases/malicious_documents.yaml` | Test case nhóm tài liệu độc hại | Không | Loader | | | Created | M7 |
| `security/runners/security_runner.py` | Chuẩn bị môi trường thử nghiệm, chạy test case qua pipeline, lưu evidence | `rag_pipeline.py`, `test_case_loader.py`, evaluator | `security_service.py` | Test cases, `RAGConfig` | Kết quả từng case | Created | M7 |
| `security/evaluators/security_result_evaluator.py` | Luật xác định (canary token) và judge để quyết pass, fail, severity | `llm_judge.py` | `security_runner.py` | Phản hồi thực tế, tiêu chí | pass/fail, severity, evidence | Created | M7 |
| `security/reports/security_report_builder.py` | Dựng báo cáo bảo mật, khuyến nghị, giới hạn độ phủ | Dữ liệu run | `report_service.py` | Dữ liệu run | File báo cáo | Created | M7 |

### 5.8 Frontend

| Đường dẫn | Trách nhiệm | Phụ thuộc | Dùng bởi | Trạng thái | Milestone |
|-----------|-------------|-----------|----------|------------|-----------|
| `frontend/Dockerfile`, `package.json`, `index.html`, `vite.config.js` | Build và chạy frontend | | `docker-compose.yml` | Implemented | M2 |
| `frontend/src/main.jsx` | Điểm vào, gắn App | `App.jsx` | Trình duyệt | Implemented | M2 |
| `frontend/src/App.jsx` | Định tuyến các trang | Pages, layouts, `AuthContext.jsx` | `main.jsx` | Implemented | M2, hoàn thiện M3 |
| `frontend/src/services/api/httpClient.js` | Gọi API, gắn token, chuẩn hóa lỗi | `VITE_API_BASE_URL` | Mọi `*Api.js` | Tested | M2 |
| `frontend/.dockerignore` | Loại `node_modules`, `dist` khỏi build context | Không | Docker build | Implemented | M2 |
| `frontend/src/services/api/healthApi.js` | Gọi `GET /health` | `httpClient.js` | `App.jsx` | Implemented | M2 |
| `frontend/src/formatting.js` | Định dạng dung lượng, ngày giờ, loại file, nhãn trạng thái và thông điệp lỗi bằng tiếng Việt | Không | Pages | Giá trị thô | Chuỗi hiển thị | Tested | M3 |
| `frontend/src/components/BackendStatus.jsx` | Chỉ báo máy chủ và database có phản hồi không (chân trang) | `healthApi.js` | `MainLayout.jsx` | | | Implemented | M3 |
| `frontend/src/styles.css` | Giao diện toàn bộ: bố cục, bảng, nút, thẻ; thích ứng màn hình nhỏ; chế độ tối | Không | `main.jsx` | | | Implemented | M3 |
| `frontend/src/test/setup.js` và các file `*.test.js(x)` | Thiết lập và test giao diện (52 test: client API, đăng nhập, bảo vệ trang, trang tài liệu, định dạng) | vitest, Testing Library | `npm test` | | | Tested | M3 |
| `frontend/src/services/api/authApi.js` | Gọi `/auth/*` | `httpClient.js` | `AuthContext.jsx`, `LoginPage.jsx` | Tested | M3 |
| `frontend/src/services/api/documentApi.js` | Gọi `/documents*` | `httpClient.js` | `DocumentsPage.jsx` | Tested | M3 |
| `frontend/src/services/api/chatApi.js` | Gọi `/chat/*` | `httpClient.js` | `ChatPage.jsx` | Created | M4 |
| `frontend/src/services/api/modelConfigApi.js` | Gọi `/model-configurations*` | `httpClient.js` | `ChatPage.jsx`, `EvaluationsPage.jsx`, `SecurityPage.jsx`, `BenchmarksPage.jsx` | Planned | M4 |
| `frontend/src/services/api/datasetApi.js` | Gọi `/datasets*`, `/dataset-versions*`, `/test-cases*` | `httpClient.js` | `DatasetsPage.jsx` | Created | M5 |
| `frontend/src/services/api/evaluationApi.js` | Gọi `/evaluations*` | `httpClient.js` | `EvaluationsPage.jsx`, `DashboardPage.jsx` | Created | M6 |
| `frontend/src/services/api/securityApi.js` | Gọi `/security/*` | `httpClient.js` | `SecurityPage.jsx` | Created | M7 |
| `frontend/src/services/api/benchmarkApi.js` | Gọi `/benchmarks*` | `httpClient.js` | `BenchmarksPage.jsx` | Created | M8 |
| `frontend/src/contexts/AuthContext.jsx` | Giữ trạng thái đăng nhập và token | `authApi.js` | `App.jsx`, `useAuth.js` | Tested | M3 |
| `frontend/src/hooks/useAuth.js` | Truy cập `AuthContext` | `AuthContext.jsx` | Pages, layout | Tested | M3 |
| `frontend/src/components/ProtectedRoute.jsx` | Chặn route khi chưa đăng nhập | `useAuth.js` | `App.jsx` | Tested | M3 |
| `frontend/src/layouts/MainLayout.jsx` | Khung chung: menu, vùng nội dung | `useAuth.js` | `App.jsx` | Implemented | M3 |
| `frontend/src/pages/LoginPage.jsx` | Đăng nhập, đăng ký | `authApi.js` | `App.jsx` | Tested | M3 |
| `frontend/src/pages/DocumentsPage.jsx` | Upload, danh sách, trạng thái, xóa | `documentApi.js` | `App.jsx` | Tested | M3 |
| `frontend/src/pages/ChatPage.jsx` | Chat và hiển thị citation | `chatApi.js`, `modelConfigApi.js` | `App.jsx` | Created | M4 |
| `frontend/src/pages/DatasetsPage.jsx` | Dataset, version, test case | `datasetApi.js` | `App.jsx` | Created | M5 |
| `frontend/src/pages/EvaluationsPage.jsx` | Run, kết quả, biểu đồ | `evaluationApi.js`, `datasetApi.js`, `modelConfigApi.js` | `App.jsx` | Created | M6 |
| `frontend/src/pages/SecurityPage.jsx` | Run bảo mật, kết quả, evidence | `securityApi.js`, `modelConfigApi.js` | `App.jsx` | Created | M7 |
| `frontend/src/pages/BenchmarksPage.jsx` | So sánh cấu hình, lịch sử | `benchmarkApi.js`, `modelConfigApi.js` | `App.jsx` | Created | M8 |
| `frontend/src/pages/DashboardPage.jsx` | Tổng quan | Các `*Api.js` | `App.jsx` | Created | M6, hoàn thiện M8 |

## 6. Điều kiện kiểm chứng

- Không có file "đầu cơ": mọi file ở mục 5 gắn với một task trong danh sách M2 đến M9.
- Mỗi file Planned đều có lý do ở mục 2 hoặc ở bảng manifest.
- Package Python: `__init__.py` được thêm khi file Python đầu tiên của thư mục đó được tạo. Hiện các thư mục `evaluation/runners`, `evaluators`, `reports`, `benchmarks`, `datasets`, `metrics/retrieval`, `metrics/generation` và các thư mục con của `security` chưa có `__init__.py`; dự án dùng package thường, không dùng namespace package.
- Khi bắt đầu mỗi milestone, đối chiếu manifest với cây thư mục thật (lệnh `find`), cập nhật trạng thái.

## 7. Quyết định đã chọn và lý do

1. **Tên adapter theo provider.** Embedding chạy cục bộ nên adapter là `local_embedder.py` (đã đổi tên từ `openai_embedder.py`). Adapter LLM giữ tên giữ chỗ `openai_llm_client.py` cho đến khi chốt LLM provider ở M4. Quy ước: mỗi adapter một file mang tên provider; đổi provider thì đổi tên file và thêm adapter, pipeline không đổi.
2. **Đã xóa các file đầu cơ ở mục 2** (đều là file rỗng). Nguyên tắc: file chỉ được tạo khi có task cần nó. Một file rỗng "để sẵn" gây hai hại: làm bản manifest nói dối về những gì đã có, và khiến người đọc tưởng đã có thiết kế cho nó. Cần lại thì tạo lại ngay khi làm task.
3. **Tách `ai_engine`, `evaluation`, `security` khỏi `backend/app`** thay vì đặt hết trong backend. Lý do: logic AI phải chạy được từ script độc lập (tiêu chí M4-T04) và dùng chung cho nhiều luồng; nếu nằm trong backend, nó dễ kéo theo phụ thuộc FastAPI và DB. *Giả định yếu:* "tách thư mục là đủ để tách phụ thuộc". Không đủ nếu không có người canh; vì thế quy tắc ở mục 4 được kiểm tra ở mỗi gate.

4. **Cấu hình mặc định của Chat**: `configs/rag_default.yaml` là giá trị mặc định; `model_config_service` tạo bản ghi `model_configurations` từ file này ở lần dùng đầu, và dùng nó khi người dùng không chọn cấu hình.

## 8. Giải thích khái niệm cho người mới

- **Manifest**: danh sách có kiểm soát của mọi file với trách nhiệm, phụ thuộc và trạng thái. Giá trị của nó là phát hiện sớm file thừa, file thiếu và phụ thuộc vòng.
- **Phụ thuộc một chiều**: tầng trên được biết tầng dưới, không ngược lại. Nếu `ai_engine` import `backend`, và `backend` import `ai_engine`, hai bên không thể thay đổi hay test riêng được nữa (phụ thuộc vòng).
- **Package Python**: thư mục có `__init__.py` mà Python import được. Vì Python không import được tên có dấu gạch ngang, thư mục package dùng snake_case.
