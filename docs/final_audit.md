# Kiểm tra cuối (M9) — 2026-11-06

Mọi kết quả dưới đây là từ lệnh chạy thật trong ngày; không có số ước lượng.

## 1. Test

| Loại | Kết quả |
|---|---|
| Backend: unit và integration | 436 pass (`RUN_MODEL_TESTS=1`, gồm 5 test với model embedding thật). Cảnh báo httpx/httpx2 của Starlette TestClient: quyết định giữ httpx và lọc đúng cảnh báo đó trong `pytest.ini` (chỉ ảnh hưởng công cụ test) |
| Giao diện: vitest | 85 pass trong 11 file; `npm run build` thành công |
| Migration | Mỗi migration mới (0007, 0008, 0009) đã downgrade rồi upgrade lại; `alembic check` không thấy khác biệt giữa model và DB |
| E2E trình duyệt (Playwright, stack Docker, model thật) | Tài liệu → Hỏi đáp → Dataset → Đánh giá → Bảo mật → Benchmark → Dashboard đều chạy tới kết quả; CSV tải được; 7 trang không tràn ngang ở 390 px; không lỗi JavaScript |
| Stack production (`deploy/`, `API_DOMAIN=localhost`) | HTTPS, HTTP chuyển sang HTTPS, header bảo mật, CORS đúng origin, khóa đăng nhập sai (429), cổng DB và backend không mở ra mạng |

## 2. Bảo mật và bí mật

| Kiểm tra | Kết quả |
|---|---|
| `.env` hoặc file secret bị track | Không; chỉ `.env.example` và `deploy/production.env.example` (giá trị mẫu) |
| Quét toàn bộ lịch sử git theo dạng key (`sk-`, `AKIA`, `ghp_`, `hf_`, private key) | Một kết quả duy nhất: chuỗi giả trong `backend/tests/unit/test_llm_client.py`, dùng để kiểm tra key không lọt vào thông báo lỗi. Không có secret thật |
| Mật khẩu dev cũ | Đã thay bằng `DEV_PASSWORD_REDACTED` trong lịch sử (làm ở M3) |
| Frontend chứa key hoặc kết nối DB | Không (NFR-04) |
| `npm audit` | 0 lỗ hổng |
| Python dependency audit | Tra OSV.dev (`scripts/audit_dependencies.py`, không cần cài công cụ). Venv máy host: 80 gói, 0 lỗ hổng. Image backend: phát hiện `pip` 24.0 và `setuptools` 79.0.1 của image gốc có lỗ hổng đã công bố, đã nâng lên 26.3 và 84.2.1 trong Dockerfile. Sau khi dựng lại: 77 gói, 0 lỗ hổng |
| Cô lập dữ liệu theo user | Có test ở mọi nhóm API (tài liệu, chat, dataset, đánh giá, bảo mật, benchmark) và ở tầng truy xuất vector; test bảo mật AC-01, AC-02 chạy thật qua pipeline |
| Giới hạn đăng nhập (R18) | Có; test tự động và kiểm tra qua proxy thật |

## 3. Kiến trúc

| Kiểm tra | Kết quả |
|---|---|
| NFR-10: một RAG pipeline | `retrieve()` và `llm.generate()` cho câu trả lời RAG chỉ được gọi trong `ai_engine/pipeline/rag_pipeline.py`. Chat, Đánh giá, Bảo mật gọi `pipeline.run`; Benchmark dùng lại runner đánh giá. `security_service` gọi `build_answer_messages` **chỉ để lấy văn bản system prompt** cho luật dò rò rỉ, không sinh câu trả lời. Judge gọi LLM riêng cho việc chấm điểm |
| Quy tắc đặt tên (CLAUDE.md §8) | Không có file, lớp hay hàm tên chung chung (helper, utils, manager, handler...). Một trường hợp chứa "data": `security/test_cases/data_leakage.yaml`, là tên nhóm tấn công trong Master Prompt (thuật ngữ miền, không phải tên chung chung), nên giữ nguyên |
| Secret qua biến môi trường | Có; compose dev trước đó **thiếu** biến `LLM_*` cho container backend, đã sửa ở M9 |

## 4. Trạng thái các gate

| Gate | Trạng thái | Còn thiếu |
|---|---|---|
| M1, M2 | Đạt (user đã duyệt) | |
| M3 Ingestion | Đạt | |
| M4 RAG | Đạt một phần | Baseline thủ công; chạy với LLM thật |
| M5 Dataset | Đạt một phần | Dataset thật do người viết và duyệt |
| M6 Đánh giá | Đạt một phần | Baseline trên dataset thật; phân tích lỗi; đo đồng thuận judge và người |
| M7 Bảo mật | Đạt một phần | 9 test cần LLM chưa chạy thật |
| M8 Benchmark | Đạt một phần | So sánh `llm_model` và `prompt_version` cần LLM; mới so `top_k` |
| M9 | Phần mã và tài liệu đạt | Deploy thật (cần tài khoản) |

## 4b. Bổ sung sau khi user giao toàn quyền (2026-11-06)

- Thêm Context Precision (tất định) và Context Recall (judge), xem `docs/metrics_notes.md` mục 5b. Bộ metric của Master Prompt giờ đã đủ.
- Xóa 2 file rỗng còn sót từ khung ban đầu (`models/report.py`, `services/report_service.py`; bảng lịch sử báo cáo để sau MVP). `scripts/seed_demo.py` trước đây rỗng, giờ là script tạo dữ liệu demo qua API (đã chạy thật, chạy lại không tạo trùng).
- Cài Ollama (LLM miễn phí chạy cục bộ) để chạy các phần cần LLM: **bị bộ kiểm duyệt an toàn chặn**, chờ user cho phép.

## 5. Rủi ro còn lại

- Một tiến trình backend (tác vụ nền, bộ đếm giới hạn đăng nhập trong bộ nhớ).
- Chưa có khoảng tin cậy cho metric; dataset nhỏ thì số dao động mạnh.
- Bộ test bảo mật nhỏ và viết tay.
- Chưa có xác minh email hay khôi phục mật khẩu.
- Máy chủ miễn phí có thể bị thu hồi; cần sao lưu database (lệnh có trong `docs/deployment_guide.md`).
