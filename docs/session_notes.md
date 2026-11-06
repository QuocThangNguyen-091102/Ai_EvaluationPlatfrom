# SESSION NOTES

## Phiên 2026-11-06 (mới nhất)

### Đã làm
- User giao làm hết phần còn lại. Hoàn thành phần mã của M3 đến M9:
  - ingestion và reprocess;
  - RAG và Chat;
  - Dataset;
  - Đánh giá (metric, LLM judge, dashboard);
  - Kiểm thử bảo mật (12 test, sandbox);
  - Benchmark;
  - giới hạn đăng nhập và đăng ký;
  - bộ deploy production (Caddy HTTPS);
  - README, kịch bản demo, kiểm tra cuối.
- Chi tiết từng phần, kết quả kiểm tra thật và lỗi tìm thấy: `docs/progress_log.md`. Tổng kết: `docs/release_audit.md`.

### Trạng thái
- Git: nhánh `main`, commit theo từng phần, **chưa có remote, chưa push**.
- Test:
  - backend 426 pass (gồm 5 test với model thật);
  - giao diện 85 pass;
  - E2E Playwright cho mọi trang trên stack Docker;
  - stack production đã chạy thử với `API_DOMAIN=localhost`.
- Migration tới `0010`.
- Docker Desktop hay tự tắt; khi lệnh docker báo không kết nối được thì mở lại Docker Desktop.

### Việc đang chờ user (chỉ user làm được)
1. **Duyệt dataset Hệ Mặt Trời:**
   - Đăng nhập tài khoản đã nạp sẵn (xem tin nhắn bàn giao), mở trang Dataset, chọn "Hệ Mặt Trời (nháp)".
   - Đọc từng câu: câu hỏi rõ chưa, đáp án đúng với câu trích chưa, câu "không có đáp án" có thật là không có không. Sửa hoặc xóa câu sai, rồi bấm "Duyệt và đóng băng".
   - Sau đó mình chạy baseline (qwen2.5:3b, judge gemma3:4b), điền `docs/error_analysis.md` và đo độ đồng thuận giữa judge và người.
2. **Deploy:** tạo remote GitHub, chạy `vercel login`, tạo máy chủ miễn phí (Oracle Cloud cần thẻ để xác minh) và tên miền; làm theo `docs/deployment_guide.md`. Không deploy thì chạy cục bộ vẫn đủ.

### Đã có sẵn trên máy (2026-11-06)
- Ollama 0.40.15 với `qwen2.5:3b` (trả lời) và `gemma3:4b` (judge). `.env` đã trỏ `LLM_BASE_URL=http://host.docker.internal:11434/v1`. Mở Ollama trước khi `docker compose up`.

### Quy tắc làm việc đã thống nhất
- Chỉ trả lời tiếng Việt (CLAUDE.md mục 1).
- Tác vụ cơ bản dùng Sonnet 5.5; task code khó cần Opus 5.5 thì báo user đổi model.

### Lưu ý
- Master Prompt gốc và danh sách task (77 task) do user dán, không lưu trong workspace. Tóm tắt nằm trong bộ nhớ dự án và `CLAUDE.md`.
- Số liệu chất lượng hiện có đều từ dataset MẪU do AI soạn (`evaluation/datasets/sample_cases_vi_two_pages.json`), chỉ để kiểm tra luồng.

## Phiên 2026-11-05
- Hoàn thành M1, M2 (user duyệt), phần đầu M3 và giao diện Tài liệu; chốt kế hoạch deploy miễn phí (`docs/11_free_deployment.md`).
