# AI Evaluation Platform

Nền tảng đánh giá RAG (Retrieval-Augmented Generation), kiểm soát chất lượng LLM và kiểm thử bảo mật AI. Gồm một ứng dụng RAG mẫu (hỏi đáp có trích dẫn trên tài liệu của người dùng) và một nền tảng đo chất lượng truy xuất, chất lượng câu trả lời, hành vi bảo mật, độ trễ và chi phí.

Trạng thái: **đang ở Milestone 2 (Foundation)**. Chưa có tính năng nào cho người dùng cuối. Tiến độ chi tiết xem [docs/progress_log.md](docs/progress_log.md).

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

Hướng dẫn chạy toàn bộ stack sẽ được viết ở M2-T08, sau khi các thành phần (database, backend, frontend) chạy được.

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
