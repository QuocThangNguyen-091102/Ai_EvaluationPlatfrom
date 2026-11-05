# SESSION NOTES

## Phiên 2026-11-05

### Đã làm
- Hoàn thành Milestone 1 và 2 (đã được user duyệt).
- Hoàn thành M3-T01 đến M3-T06, M3-T08 phần 1 (danh sách, chi tiết, xóa) và M3-T09 (giao diện đăng nhập và trang Tài liệu).
- Có giao diện thật: đăng nhập, đăng ký, trang Tài liệu (upload kéo thả, danh sách, xóa), chế độ tối, thích ứng điện thoại; đã kiểm tra bằng trình duyệt tự động trên stack Docker.
- Chốt kế hoạch deploy miễn phí (`docs/11_free_deployment.md`): giao diện lên Vercel, backend ở nơi chạy container đủ RAM.
- Kết quả kiểm tra thật và lỗi tìm thấy của từng task: `docs/progress_log.md`.

### Trạng thái
- Git: nhánh `main`, commit theo từng task, **chưa có remote, chưa push**.
- Test: backend 172 pass và 5 test model thật (chạy bằng `RUN_MODEL_TESTS=1`, đã pass); giao diện 52 pass.
- Docker Desktop hay tự tắt; mở lại khi lệnh docker báo không kết nối được. Stack chạy bằng `docker compose up --build`.
- Backend image 2,2 GB, model cần khoảng 0,93 GB RAM (đã đo).
- Chưa làm: ingestion hoàn chỉnh (nối parse, chunk, embed, lưu vector), reprocess, RAG và Chat, Dataset, Evaluation, Security, Benchmark và các trang giao diện tương ứng.

### Việc đang chờ user
1. **M3-T07 (Ingestion service) là task khó [C]: cần đổi sang Opus 5.5** (`/model opus`) rồi bảo mình làm tiếp.
2. Tạo remote GitHub nếu muốn push (cần cho việc deploy).
3. Về lâu dài: tạo tài khoản các dịch vụ miễn phí khi tới M9-T04 (chỉ bạn làm được); quyết định có đăng ký thẻ để xác minh tài khoản không.
4. Cảnh báo `httpx`/`httpx2` của pytest: bỏ qua hay xử lý.
5. LLM provider: quyết định ở M4.

### Quy tắc làm việc đã thống nhất
- Chỉ trả lời tiếng Việt (CLAUDE.md mục 1). Mỗi milestone xong thì dừng chờ duyệt.
- Tác vụ cơ bản dùng Sonnet 5.5. Khi gặp task code khó cần Opus 5.5 (ví dụ M3-T07, M4-T02, M4-T04) thì dừng và báo user để tự đổi model.

### Việc tiếp theo
- M3-T07 (cần Opus), sau đó phần reprocess của M3-T08, rồi gate M3.

### Lưu ý
- Master Prompt gốc và danh sách task (`Kiến trúc.txt`, 77 task) do user dán, không lưu trong workspace. Tóm tắt nằm trong bộ nhớ dự án và `CLAUDE.md`.
- Mở Claude Code ở thư mục `ai-evaluation-platform` để `CLAUDE.md` được nạp tự động.
- Docker Desktop đã tự tắt hai lần trong phiên; khi lệnh docker báo không kết nối được daemon thì mở lại Docker Desktop.
