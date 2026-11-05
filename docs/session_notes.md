# SESSION NOTES

## Phiên 2026-11-05

### Đã làm
- Dựng lại repo `ai-evaluation-platform/`, tạo `CLAUDE.md` (có quy ước đặt tên), `docs/progress_log.md`.
- Hoàn thành Milestone 1 (M1-T01 đến M1-T11): tài liệu thiết kế `docs/01` đến `docs/10`. M1-T11 do một agent độc lập rà mâu thuẫn, đã sửa các điểm xác nhận được.
- Hoàn thành Milestone 2 (M2-T01 đến M2-T08): git repo, backend FastAPI, PostgreSQL + pgvector bằng Docker Compose, Alembic, frontend Vite + React, logging, xử lý lỗi chuẩn, pytest. Gate M2 đã kiểm tra bằng clone sạch.
- Chốt embedding chạy cục bộ (phương án A3): model `intfloat/multilingual-e5-small`, 384 chiều. Không cần API key cho embedding.
- Hoàn thành M3-T01: models và migration `0002` cho `users`, `documents`, `document_chunks`.
- User duyệt gate M1 và M2. Hoàn thành M3-T02: đăng ký, đăng nhập, `/auth/me` (53 test pass).
- Hoàn thành M3-T03: upload, kiểm tra loại file và dung lượng, lưu file gốc vào volume `uploads` (93 test pass).
- Chi tiết và kết quả kiểm tra thật của từng task: `docs/progress_log.md`.

### Trạng thái
- Git: nhánh `main`, các commit theo từng task, **chưa có remote, chưa push**.
- Stack Docker: db và backend đang chạy (nếu Docker Desktop đang mở); `docker compose up --build` để chạy đủ.
- File `.env` cục bộ (không commit) dùng một mật khẩu dev cục bộ. Lịch sử git đã được viết lại để xóa mật khẩu này khỏi mọi commit.
- Chưa có tính năng cho người dùng cuối. Chưa kiểm tra giao diện bằng trình duyệt thật.
- Đã chạy thử model embedding thật: vector đúng 384 chiều; truy xuất chéo ngôn ngữ yếu; chunk phải ngắn hơn 512 token (chi tiết `docs/06_deployment_tech.md`). Thử rất nhỏ, chưa phải đo chất lượng. M3-T06 vẫn có test `len(vector) == 384` trong code dự án.

### Việc đang chờ user
1. Tạo remote GitHub rồi push (M2-T01 còn thiếu bước này).
2. Cảnh báo `httpx`/`httpx2` của pytest: bỏ qua hay xử lý.
3. LLM provider: quyết định ở M4 (thử gói miễn phí hoặc LLM cục bộ).

### Quy tắc làm việc đã thống nhất
- Chỉ trả lời tiếng Việt (CLAUDE.md mục 1). Mỗi milestone xong thì dừng chờ duyệt.
- Tác vụ cơ bản dùng Sonnet 5.5. Khi gặp task code khó cần Opus 5.5 (ví dụ M3-T07, M4-T02, M4-T04) thì dừng và báo user để tự đổi model.

### Việc tiếp theo
- M3-T04 (parsers TXT, PDF, DOCX). M3-T07 (Ingestion service) là task khó [C]: dừng và báo user đổi sang Opus 5.5 trước khi làm.

### Lưu ý
- Master Prompt gốc và danh sách task (`Kiến trúc.txt`, 77 task) do user dán, không lưu trong workspace. Tóm tắt nằm trong bộ nhớ dự án và `CLAUDE.md`.
- Mở Claude Code ở thư mục `ai-evaluation-platform` để `CLAUDE.md` được nạp tự động.
- Docker Desktop đã tự tắt hai lần trong phiên; khi lệnh docker báo không kết nối được daemon thì mở lại Docker Desktop.
