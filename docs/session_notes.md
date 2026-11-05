# SESSION NOTES

## Phiên 2026-11-05

### Đã làm
- Dựng lại repo `ai-evaluation-platform/` từ đầu, tạo `CLAUDE.md` (có mục 8 quy ước đặt tên), `docs/progress_log.md`.
- Đổi tên các file vi phạm quy ước đặt tên (`seed_demo.py`, `session_notes.md`, các file `docs/01` đến `docs/10` theo danh sách task M1).
- Làm M1-T01 đến M1-T10 (bản nháp chờ duyệt), nội dung ở `docs/01_feasibility.md` đến `docs/10_test_risk_learning.md`. Ghi kết quả từng task ở `docs/progress_log.md`.
- Xóa 4 file rỗng đầu cơ và thư mục `docs/diagrams/` (xem M1-T09).

### Trạng thái
- Milestone 1: còn **M1-T11 (Gate review)**: đọc lại `docs/01` đến `docs/10`, tìm mâu thuẫn, sửa, rồi user duyệt.
- Chưa có code, chưa có test. Sơ đồ Mermaid chưa được render thử.

### Quyết định đã chọn (user giao Claude tự chọn, có lý do trong từng tài liệu)
1. Provider: A1, một provider cho LLM và embedding, cài sau interface (`06_deployment_tech.md` mục 4). Đổi được miễn phí trước M3-T01; cần gọi thử provider để xác minh API key và chi phí trước M3-T01.
2. Ingestion chạy nền bằng BackgroundTasks, file gốc lưu volume cục bộ, evaluation và security chạy dưới user sở hữu tài liệu (`04_architecture.md` mục 6 và 7).
3. Giữ `document_chunks.user_id`; benchmark MVP chỉ đổi biến phía sinh; version đã duyệt bất biến ở Service (`07_database.md` mục 9).
4. Thêm nhóm `/model-configurations`; sửa version đã duyệt trả 409; import từ chối cả file nếu có dòng lỗi (`08_api_contracts.md` mục 13).
5. Mỗi tài liệu T06 đến T10 có thêm phần phản biện giả định yếu và giải thích khái niệm cho người mới (theo vai trò mentor trong `CLAUDE.md`).

### Việc tiếp theo
- User xem lại các tài liệu M1, nếu không đồng ý quyết định nào thì nói để sửa, rồi giao M1-T11.
- Không sang Milestone 2 khi gate M1 chưa được duyệt.

### Lưu ý
- Master Prompt gốc và danh sách task (`Kiến trúc.txt`, 77 task) do user dán, không lưu trong workspace. Tóm tắt nằm trong bộ nhớ dự án và `CLAUDE.md`.
- Mở Claude Code ở thư mục `ai-evaluation-platform` để `CLAUDE.md` được nạp tự động.
