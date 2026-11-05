# SESSION NOTES

## Phiên 2026-11-05

### Đã làm
- Dựng lại repo `ai-evaluation-platform/`, tạo `CLAUDE.md` (có quy ước đặt tên), `docs/progress_log.md`.
- Hoàn thành Milestone 1 (M1-T01 đến M1-T11): tài liệu thiết kế `docs/01` đến `docs/10`. M1-T11 do một agent độc lập rà mâu thuẫn, đã sửa các điểm xác nhận được.
- Hoàn thành Milestone 2 (M2-T01 đến M2-T08): git repo, backend FastAPI, PostgreSQL + pgvector bằng Docker Compose, Alembic, frontend Vite + React, logging, xử lý lỗi chuẩn, pytest. Gate M2 đã kiểm tra bằng clone sạch.
- Chi tiết và kết quả kiểm tra thật của từng task: `docs/progress_log.md`.

### Trạng thái
- Git: nhánh `main`, các commit theo từng task, **chưa có remote, chưa push**.
- Stack Docker hiện đang dừng (`docker compose up --build` để chạy lại). Volume `ai-evaluation-platform_pgdata` còn dữ liệu cũ.
- File `.env` cục bộ (không commit) dùng mật khẩu dev `DEV_PASSWORD_REDACTED`.
- Chưa có tính năng cho người dùng cuối. Chưa kiểm tra giao diện bằng trình duyệt thật.

### Việc đang chờ user
1. **Chặn M3-T01:** điều kiện vào M3-T01 là gọi thử provider để chốt embedding model và số chiều vector (`06_deployment_tech.md` mục 4). Cần user cung cấp API key của provider đã chọn (A1) hoặc chuyển sang A3 (embedding cục bộ).
2. Tạo remote GitHub rồi push (M2-T01 còn thiếu bước này).
3. Mật khẩu dev `DEV_PASSWORD_REDACTED` nằm trong 2 commit cũ của `conftest.py`: giữ nguyên hay viết lại lịch sử trước lần push đầu.
4. Cảnh báo `httpx`/`httpx2` của pytest: bỏ qua hay xử lý.
5. Duyệt gate Milestone 2.

### Quy tắc làm việc đã thống nhất
- Chỉ trả lời tiếng Việt (CLAUDE.md mục 1). Mỗi milestone xong thì dừng chờ duyệt.
- Tác vụ cơ bản dùng Sonnet 5.5. Khi gặp task code khó cần Opus 5.5 (ví dụ M3-T07, M4-T02, M4-T04) thì dừng và báo user để tự đổi model.

### Việc tiếp theo
- Sau khi user giải quyết mục 1 và duyệt gate M2: bắt đầu M3-T01 (models và migration cho users, documents, document_chunks).

### Lưu ý
- Master Prompt gốc và danh sách task (`Kiến trúc.txt`, 77 task) do user dán, không lưu trong workspace. Tóm tắt nằm trong bộ nhớ dự án và `CLAUDE.md`.
- Mở Claude Code ở thư mục `ai-evaluation-platform` để `CLAUDE.md` được nạp tự động.
