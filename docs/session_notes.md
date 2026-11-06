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
- Migration tới `0009`.
- Docker Desktop hay tự tắt; khi lệnh docker báo không kết nối được thì mở lại Docker Desktop.

### Việc đang chờ user (chỉ user làm được)
1. **Dataset thật:**
   - chọn corpus có quyền dùng (`docs/corpus_sources.md`);
   - viết khoảng 100 câu có tham chiếu, gồm câu không có đáp án;
   - duyệt trên trang Dataset.
   - Sau đó chạy đánh giá baseline và điền `docs/error_analysis.md`, `docs/baseline_manual.md`.
2. **LLM:** điền `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` trong `.env`, rồi chạy lại đánh giá, bảo mật (9 test cần LLM) và benchmark theo `llm_model` hoặc `prompt_version`.
3. **Deploy:** tạo remote GitHub, tài khoản Vercel, máy chủ miễn phí, tên miền; làm theo `docs/deployment_guide.md`.
4. Cho phép cài **Ollama** (LLM miễn phí chạy cục bộ). Lệnh cài bị bộ kiểm duyệt an toàn chặn; có Ollama thì tự chạy được đánh giá có LLM, 9 test bảo mật còn lại và benchmark theo model.

### Quy tắc làm việc đã thống nhất
- Chỉ trả lời tiếng Việt (CLAUDE.md mục 1).
- Tác vụ cơ bản dùng Sonnet 5.5; task code khó cần Opus 5.5 thì báo user đổi model.

### Lưu ý
- Master Prompt gốc và danh sách task (77 task) do user dán, không lưu trong workspace. Tóm tắt nằm trong bộ nhớ dự án và `CLAUDE.md`.
- Số liệu chất lượng hiện có đều từ dataset MẪU do AI soạn (`evaluation/datasets/sample_cases_vi_two_pages.json`), chỉ để kiểm tra luồng.

## Phiên 2026-11-05
- Hoàn thành M1, M2 (user duyệt), phần đầu M3 và giao diện Tài liệu; chốt kế hoạch deploy miễn phí (`docs/11_free_deployment.md`).
