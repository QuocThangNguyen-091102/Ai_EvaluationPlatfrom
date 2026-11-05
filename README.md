# AI Evaluation Platform

Nền tảng đánh giá RAG (Retrieval-Augmented Generation), kiểm soát chất lượng LLM và kiểm thử bảo mật AI. Gồm một ứng dụng RAG mẫu (hỏi đáp có trích dẫn trên tài liệu của người dùng) và một nền tảng đo chất lượng truy xuất, chất lượng câu trả lời, hành vi bảo mật, độ trễ và chi phí.

Trạng thái: **Milestone 2 (Foundation) đã xong, chờ duyệt gate; tiếp theo là Milestone 3 (Ingestion)**. Stack chạy được và có health check, nhưng chưa có tính năng nào cho người dùng cuối. Tiến độ chi tiết xem [docs/progress_log.md](docs/progress_log.md).

## Công nghệ

Python, FastAPI, PostgreSQL + pgvector, React (Vite), Docker Compose, Git. Lý do chọn và các phương án thay thế: [docs/06_deployment_tech.md](docs/06_deployment_tech.md).

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---------|----------|
| `backend/` | FastAPI: API, service, repository, migration, test |
| `ai_engine/` | Logic AI dùng chung: ingestion, chunking, embedding, retrieval, generation, RAG pipeline |
| `evaluation/` | Dataset loader, metrics, evaluation runner, benchmark, báo cáo |
| `security/` | Test case bảo mật, runner, evaluator, báo cáo |
| `frontend/` | Giao diện React |
| `configs/` | Cấu hình mặc định (model, RAG) |
| `docs/` | Tài liệu thiết kế, nhật ký tiến độ |

Danh sách file và trách nhiệm từng file: [docs/09_repo_manifest.md](docs/09_repo_manifest.md).

## Cài đặt và chạy

Yêu cầu: Docker Desktop (có Docker Compose), Git. Muốn chạy test trên máy host thì cần thêm Python 3.11.

```bash
git clone <địa chỉ repo> ai-evaluation-platform
cd ai-evaluation-platform

# 1. Tạo file cấu hình rồi đổi giá trị mật khẩu
cp .env.example .env
#    Sửa POSTGRES_PASSWORD, và phần mật khẩu trong DATABASE_URL cho khớp.
#    Đổi JWT_SECRET thành một chuỗi ngẫu nhiên dài ít nhất 32 ký tự (xem hướng dẫn trong .env.example).

# 2. Dựng và chạy toàn bộ stack (db, backend, frontend)
docker compose up --build
```

Khi các service đều ở trạng thái healthy (`docker compose ps`):

| Thành phần | Địa chỉ |
|------------|---------|
| Frontend | http://localhost:5173 |
| Backend (tài liệu API tự sinh) | http://localhost:8000/docs |
| Kiểm tra sức khỏe | http://localhost:8000/health (trả `{"status":"ok","database":"ok"}`) |
| PostgreSQL (chỉ từ máy host) | 127.0.0.1:5432 |

Migration chạy tự động khi backend khởi động (`alembic upgrade head`). Dữ liệu database nằm trong volume `pgdata` nên còn sau `docker compose down`. Muốn xóa cả dữ liệu: `docker compose down -v`.

Nếu cổng 5432, 8000 hoặc 5173 đã bị chiếm, đổi `DB_HOST_PORT`, `BACKEND_HOST_PORT`, `FRONTEND_HOST_PORT` trong `.env`.

### Chạy test backend

```bash
docker compose up -d db                    # test integration cần database
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt     # Windows; Linux/macOS: .venv/bin/python
.venv/Scripts/python -m pytest             # toàn bộ
.venv/Scripts/python -m pytest -m "not integration"            # chỉ unit, không cần database
```

Lưu ý: nếu bạn đổi `POSTGRES_PASSWORD` thì đặt `DATABASE_URL` trong `.env` cho khớp để test trên máy host kết nối được.

## Quy ước làm việc

**Commit.** Mỗi task một commit riêng. Thông điệp theo dạng `loại(phạm vi): mô tả ngắn (mã task)`, ví dụ `feat(ingestion): add TXT/PDF/DOCX parsers (M3-T04)`.

| Loại | Dùng khi |
|------|----------|
| `feat` | Thêm tính năng |
| `fix` | Sửa lỗi |
| `docs` | Chỉ sửa tài liệu |
| `test` | Thêm hoặc sửa test |
| `chore` | Hạ tầng, cấu hình, dọn dẹp |
| `refactor` | Đổi cấu trúc, không đổi hành vi |

**Branch.** `main` luôn ở trạng thái chạy được. Một người làm nên commit trực tiếp lên `main` sau khi task đạt "Hoàn thành khi"; khi cần thử nghiệm rủi ro thì tạo branch `task/<mã-task>-<mô-tả-ngắn>`.

**Bí mật.** API key và mật khẩu chỉ nằm trong file `.env` (đã bị `.gitignore` loại). Chỉ `.env.example` được commit, và chỉ chứa giá trị mẫu.

**Đặt tên.** Theo mục 8 của [CLAUDE.md](CLAUDE.md).

## Giới hạn đã biết

Dự án đang xây dựng theo từng milestone có kiểm tra; mọi con số về chất lượng hoặc hiệu năng chỉ được công bố sau khi có run thật.
