# AI Evaluation Platform

Nền tảng đánh giá RAG (Retrieval-Augmented Generation), kiểm soát chất lượng LLM và kiểm thử bảo mật AI. Gồm một ứng dụng RAG mẫu (hỏi đáp có trích dẫn trên tài liệu của người dùng) và một nền tảng đo chất lượng truy xuất, chất lượng câu trả lời, hành vi bảo mật, độ trễ và chi phí.

Trạng thái: **đủ chức năng của MVP (M1 đến M9)**. Một số gate chỉ đạt một phần vì cần người làm: dataset thật, baseline, LLM (xem mục [Việc còn cần người](#việc-còn-cần-người)). Tiến độ chi tiết: [docs/progress_log.md](docs/progress_log.md). Kết quả kiểm tra cuối: [docs/final_audit.md](docs/final_audit.md).

## Chức năng

| Trang | Làm được gì |
|---|---|
| Tài liệu | Upload PDF, DOCX, TXT (kéo thả); xử lý nền: parse, làm sạch, chia chunk, embed; xem trạng thái, xóa, xử lý lại với cấu hình chunk khác |
| Hỏi đáp | Hỏi trên tài liệu của mình. Câu trả lời có trích dẫn nguồn và trang; hệ thống từ chối khi tài liệu không đủ thông tin; có lịch sử phiên, độ trễ, token, chi phí |
| Dataset | Bộ câu hỏi đánh giá có phiên bản: câu trích tham chiếu được định vị chính xác trong tài liệu; nhập CSV hoặc JSON; duyệt và đóng băng |
| Đánh giá | Chạy bộ câu hỏi qua RAG pipeline. Metric: Precision, Recall, MRR, NDCG, Context Precision, hành vi đúng; Context Recall, faithfulness, answer relevancy (LLM judge). Phân loại lỗi từng câu; báo cáo CSV |
| Bảo mật | 12 test trong 5 nhóm: prompt injection, jailbreak, rò rỉ dữ liệu, kiểm soát truy cập, tài liệu độc. Chạy trong sandbox riêng; có bằng chứng, mức độ, cách giảm thiểu và giới hạn của lượt chạy |
| Benchmark | So sánh nhiều cấu hình (đổi một biến: top_k, LLM model hoặc prompt) trên cùng dataset: chất lượng, độ trễ p50 và p95, token, chi phí |
| Dashboard | Tổng quan 6 khu vực; so sánh các lượt đánh giá theo phiên bản dataset |

**Không cần LLM để chạy.** Khi chưa cấu hình `LLM_BASE_URL`, hệ thống chạy **chế độ trích đoạn**: trả các đoạn liên quan nhất kèm nguồn. Embedding chạy cục bộ (`intfloat/multilingual-e5-small`), không cần API key. Khi có LLM tương thích OpenAI, chỉ cần điền 3 biến môi trường.

## Kiến trúc

Modular monolith: FastAPI + SQLAlchemy + PostgreSQL/pgvector, giao diện React (Vite).

**Chỉ có một RAG pipeline** (`ai_engine/pipeline/rag_pipeline.py`), dùng chung cho Hỏi đáp, Đánh giá, Bảo mật và Benchmark. Nhờ vậy, điều được đo chính là điều người dùng nhận được. Truy xuất luôn lọc theo user ngay trong câu SQL.

| Thư mục | Nội dung |
|---------|----------|
| `backend/` | FastAPI: API, service, repository, migration (Alembic), test |
| `ai_engine/` | Ingestion, chunking, embedding, retrieval, generation, RAG pipeline |
| `evaluation/` | Dataset, metric, LLM judge, runner đánh giá, benchmark, báo cáo |
| `security/` | Test case YAML, runner, bộ chấm theo luật, báo cáo độ phủ |
| `frontend/` | Giao diện React |
| `configs/` | Cấu hình RAG mặc định, bảng giá model |
| `deploy/` | Compose cho môi trường thật (Caddy HTTPS) |
| `docs/` | Thiết kế, ghi chú metric, kiểm thử bảo mật, benchmark, triển khai, nhật ký |

Chi tiết: [docs/04_architecture.md](docs/04_architecture.md), [docs/07_database.md](docs/07_database.md), [docs/08_api_contracts.md](docs/08_api_contracts.md), danh sách file [docs/09_repo_manifest.md](docs/09_repo_manifest.md).

## Cài đặt và chạy (máy cục bộ)

Yêu cầu: Docker Desktop (có Docker Compose), Git. Muốn chạy test trên máy host thì cần thêm Python 3.11 và Node 20+.

```bash
git clone <địa chỉ repo> ai-evaluation-platform
cd ai-evaluation-platform

# 1. Tạo file cấu hình rồi đổi giá trị mật khẩu
cp .env.example .env
#    Sửa POSTGRES_PASSWORD, và phần mật khẩu trong DATABASE_URL cho khớp.
#    Đổi JWT_SECRET thành một chuỗi ngẫu nhiên dài ít nhất 32 ký tự (xem hướng dẫn trong .env.example).
#    LLM tùy chọn: điền LLM_BASE_URL, LLM_MODEL, LLM_API_KEY (để trống: chế độ trích đoạn).

# 2. Dựng và chạy toàn bộ stack (db, backend, frontend)
docker compose up --build
```

Khi các service đều ở trạng thái healthy (`docker compose ps`):

| Thành phần | Địa chỉ |
|------------|---------|
| Giao diện | http://localhost:5173 |
| Backend (tài liệu API tự sinh) | http://localhost:8000/docs |
| Kiểm tra sức khỏe | http://localhost:8000/health |

- Lần đầu xử lý tài liệu, backend tải model embedding (vài trăm MB) vào volume `models`.
- Migration chạy tự động khi backend khởi động.
- Dữ liệu nằm trong volume nên còn lại sau `docker compose down`; muốn xóa cả dữ liệu thì dùng `docker compose down -v`.
- Nếu cổng bị chiếm, đổi `DB_HOST_PORT`, `BACKEND_HOST_PORT`, `FRONTEND_HOST_PORT` trong `.env`.

### Dùng LLM miễn phí chạy trên máy (Ollama)

1. Cài Ollama từ https://ollama.com/download, rồi tải model:
   ```bash
   ollama pull qwen2.5:3b     # trả lời (tiếng Việt tốt, nhẹ, chạy được bằng CPU)
   ollama pull gemma3:4b      # judge: khác họ model với model trả lời để giảm thiên lệch
   ```
2. Thêm vào `.env`, rồi chạy `docker compose up -d backend`:
   ```
   LLM_BASE_URL=http://host.docker.internal:11434/v1
   LLM_MODEL=qwen2.5:3b
   LLM_PROVIDER_NAME=ollama
   LLM_TIMEOUT_SECONDS=300
   ```
3. Trên trang Đánh giá, Bảo mật hoặc Benchmark, nhập `gemma3:4b` vào ô judge model.

Trên máy thử (i5 thế hệ 11, không GPU, 20 GB RAM), mỗi câu trả lời mất khoảng 2–15 giây và mỗi lần judge chấm khoảng 12–40 giây.

Dữ liệu demo tạo sẵn: `python scripts/seed_demo.py --email ban@example.com --password "mat-khau-dai"`. Kịch bản demo từng bước: [docs/demo_script.md](docs/demo_script.md).

## Triển khai miễn phí lên internet

Giao diện chạy trên Vercel; API, database và model chạy trên một máy chủ miễn phí sau Caddy (HTTPS). Hướng dẫn từng bước: [docs/deployment_guide.md](docs/deployment_guide.md). Lý do chọn kiến trúc này: [docs/11_free_deployment.md](docs/11_free_deployment.md).

Các bảo vệ cho bản công khai:
- giới hạn số lần đăng nhập sai và số lần đăng ký;
- công tắc đóng đăng ký;
- giới hạn số tài liệu và dung lượng mỗi file;
- database không mở ra ngoài;
- header bảo mật ở Caddy.

## Chạy test

```bash
# Backend: cần database đang chạy
docker compose up -d db
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt     # Windows; Linux/macOS: .venv/bin/python
.venv/Scripts/python -m pytest                                  # toàn bộ
.venv/Scripts/python -m pytest -m "not integration"             # chỉ unit, không cần database
RUN_MODEL_TESTS=1 .venv/Scripts/python -m pytest                # thêm test với model embedding thật (chậm)

# Giao diện
cd frontend
npm install
npm test
npm run build
```

Nếu bạn đổi `POSTGRES_PASSWORD`, hãy đặt `DATABASE_URL` trong `.env` cho khớp để test trên máy host kết nối được.

Kết quả lần chạy cuối (2026-11-06):
- backend 436 test pass (gồm 5 test với model thật);
- giao diện 85 test pass;
- E2E trên trình duyệt thật với stack Docker cho mọi trang chính, cả cỡ màn hình điện thoại.

## Việc còn cần người

| Việc | Vì sao mình không tự làm |
|---|---|
| Viết và duyệt dataset thật (khoảng 100 câu, có câu không có đáp án) | Dataset dùng để đo phải do người viết và duyệt; số liệu từ dataset do AI soạn không có giá trị đo |
| Chạy baseline, phân tích lỗi ([docs/error_analysis.md](docs/error_analysis.md)) | Cần dataset thật |
| Cấu hình LLM rồi chạy lại đánh giá và 9 test bảo mật cần LLM | Cần tài khoản hoặc key của bạn |
| Tạo remote GitHub, tài khoản Vercel và máy chủ, tên miền | Cần tài khoản của bạn |

## Giới hạn đã biết

- **Một tiến trình backend.** Tác vụ nền chạy trong tiến trình web; khởi động lại thì tác vụ dở bị đánh dấu lỗi và phải chạy lại.
- **Chế độ trích đoạn không biết từ chối.** Câu không có đáp án bị xếp loại "bịa"; cần LLM để đo hành vi từ chối.
- **Metric phụ thuộc dataset.** LLM judge có thiên lệch ([docs/metrics_notes.md](docs/metrics_notes.md)); chưa có khoảng tin cậy.
- **Kiểm thử bảo mật chỉ phủ 12 kịch bản**; không kết luận hệ thống an toàn tuyệt đối ([docs/security_testing.md](docs/security_testing.md)).
- **Chưa có** khôi phục mật khẩu, xác minh email, xuất PDF.
- Mọi số liệu chất lượng trong repo hiện chỉ từ dataset MẪU để kiểm tra luồng, **không phải kết quả đo thật**.

## Quy ước làm việc

- **Commit:** mỗi task một commit; `main` luôn chạy được.
- **Bí mật:** chỉ nằm trong `.env` hoặc `deploy/production.env`; cả hai bị `.gitignore` loại.
- **Đặt tên:** theo mục 8 của [CLAUDE.md](CLAUDE.md).
