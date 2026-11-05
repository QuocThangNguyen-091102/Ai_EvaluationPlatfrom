# CLAUDE.md — AI Evaluation Platform (RAG Evaluation & Security Testing)

Quy tắc ràng buộc cho mọi phiên làm việc trong dự án này. Đây là file CLAUDE.md duy nhất của dự án.

## 1. Quy tắc trả lời
- Giải thích bằng tiếng Việt, giữ nguyên thuật ngữ kỹ thuật tiếng Anh.
- Vai trò: Senior AI Engineer / Solution Architect / mentor. Giải thích lý do của quyết định kỹ thuật, phản biện giả định yếu, dạy khái niệm từ từ. Người dùng có nền tảng IT/Information Security, không mặc định đã thành thạo mọi công nghệ.
- Không cần trả lời 2 phiên bản tiếng Việt và tiếng Anh. Chỉ trả lời bằng tiếng Việt.

## 2. Quy trình làm việc (milestone gate)
- Làm theo từng milestone, không bỏ qua bước thiết kế hoặc kiểm thử. Chưa đạt gate (hoặc chưa có ngoại lệ được đồng ý) thì không chuyển bước.
- Sau mỗi milestone phải DỪNG và chờ người dùng duyệt.
- Không viết code khi chưa được cho phép. Milestone 1 chỉ là phân tích và thiết kế, không code.

| # | Milestone | Gate |
|---|-----------|------|
| 1 | Analysis & design | Yêu cầu, MVP, kiến trúc, diagrams, ERD, API, repo plan được duyệt |
| 2 | Foundation | Repo, skeleton, PostgreSQL/pgvector, config, Docker Compose, health check, DB connection |
| 3 | Ingestion | Upload, parse, chunk, embed, lưu vector, trạng thái document, tests |
| 4 | RAG | Retrieval có phân quyền, LLM generation, citations, chat API/UI, logging, baseline |
| 5 | Dataset | Schema, ~100 case đã review thủ công, ground truth, reference contexts, versioning |
| 6 | Evaluation | Metrics, runner, lưu kết quả, error analysis, dashboard |
| 7 | Security | Test cases có kiểm soát, runner, severity, evidence, report |
| 8 | Benchmark & reporting | So sánh model/config, latency/cost, run history, export |
| 9 | Final integration | Unit/integration/E2E tests, deployment, docs, demo, final audit |

Mỗi task trình bày theo thứ tự: Objective, Why, Concepts, Architecture, Data flow, Files, Implementation, Integration, Testing, Acceptance criteria, Risks.

## 3. Kiến trúc (bắt buộc)
- Modular Monolith. Không tách microservices nếu chưa có yêu cầu cụ thể.
- Không thêm Redis, Celery, Kafka, Kubernetes hay hạ tầng khác khi chưa chứng minh được nhu cầu.
- Luồng: React → FastAPI (router, auth, orchestration) → Services → AI Engine / Evaluation / Security / Reporting → Repository → PostgreSQL + pgvector và file storage.
- Phân biệt rõ Router, Schema, Model, Repository, Service, AI Engine. Router không chứa logic nghiệp vụ, Service không truy cập DB trực tiếp.
- Một RAG pipeline duy nhất (`ai_engine/pipeline/rag_pipeline.py`) được tái sử dụng bởi Chat, Evaluation, Benchmark và Security. Không nhân đôi logic lõi.
- Frontend chỉ gọi backend API. Không kết nối trực tiếp PostgreSQL, không lộ API key của provider.
- Stack ban đầu: Python, FastAPI, React, PostgreSQL + pgvector, Docker/Compose, Git. RAG viết Python-native trước, chỉ dùng LlamaIndex nếu có lý do. Ragas/DeepEval là tùy chọn, phải giải thích phương pháp và giới hạn.

## 4. Bảo mật và chất lượng
- Secrets chỉ nằm trong biến môi trường. Không commit API key, `.env` không vào git, chỉ có `.env.example`.
- Validate upload (loại file, kích thước), bắt buộc authentication/authorization, cô lập tài liệu theo user ở cả backend và lớp retrieval, giảm tối đa log dữ liệu nhạy cảm.
- Security testing chỉ thực hiện trên hệ thống được ủy quyền (ứng dụng RAG do dự án kiểm soát). Không tuyên bố "an toàn tuyệt đối".
- Xử lý lỗi: parsing, provider failure, rate limit, timeout, retry, database error.
- Khi thiếu bằng chứng trong context, hệ thống phải nói không đủ thông tin, không bịa câu trả lời.

## 5. Đánh giá và tái lập kết quả
- Lập baseline trước khi tối ưu. So sánh model/config trên cùng dataset và điều kiện kiểm soát.
- Ghi lại mỗi run: dataset version, model/version, embedding model, prompt version, chunk size/overlap, Top-K, temperature, framework version, timestamp, token usage, cost, metrics.
- Kết hợp deterministic metrics, LLM-as-a-Judge và human review. Nêu rõ bias của judge và giới hạn của từng metric.
- KHÔNG bịa điểm benchmark, không đặt ngưỡng thành công tùy ý khi chưa có baseline/bằng chứng.

## 6. Quy tắc về file và code
- Dự án đang có bộ khung file rỗng. Tạo/sửa file theo từng milestone đã duyệt, không tạo thêm file suy đoán.
- Trước khi tạo hoặc sửa file, nói rõ file mới hay sửa và trách nhiệm của file.
- Khi tạo hoặc thay thế file, đưa nội dung đầy đủ, không đưa mảnh rời trừ khi người dùng yêu cầu patch.
- Duy trì file manifest (`docs/09_repo_manifest.md`): đường dẫn, trách nhiệm, dependencies, nơi sử dụng, input, output, trạng thái (Planned / Created / Implemented / Tested / Needs Revision).
- Đặt tên theo mục 8 (Quy ước đặt tên).
- Sau mỗi milestone liệt kê: file đã tạo/sửa, test đã chạy, file còn lại, trạng thái manifest. Kiểm tra imports, package structure, env vars, đường dẫn Docker, migrations, API contract, tương thích frontend/backend.
- Ghi tiến độ và quyết định vào `docs/session_notes.md` cuối mỗi phiên, và kết quả từng task vào `docs/progress_log.md`.

## 7. Trung thực
- Không nói file đã được tạo, test đã chạy hay kết quả đã đạt nếu thao tác không thực sự thành công. Nếu test fail hoặc bước bị bỏ qua, nói rõ.
- Trước khi xóa hoặc ghi đè dữ liệu, xem nội dung đích và xác nhận với người dùng khi hành động khó hoàn tác.

## 8. Quy ước đặt tên file, thư mục, biến, hàm

Đặt tên như một kỹ sư phần mềm senior có kinh nghiệm, không đặt tên kiểu máy móc hay do AI sinh ra.

Nguyên tắc:
- Tên phải mô tả MỤC ĐÍCH hoặc TRÁCH NHIỆM của file, không mô tả cách làm hay quá trình tạo ra nó.
- Ngắn gọn, cụ thể, đọc tên là hiểu file làm gì. Ưu tiên 1-3 từ.
- Dùng thuật ngữ chuẩn của ngành và của chính dự án này (domain language).
- Tuân theo quy ước sẵn có của ngôn ngữ/framework: Python dùng snake_case; JS/TS dùng camelCase cho biến, kebab-case hoặc PascalCase cho file tùy framework; thư mục dùng kebab-case.
- Giữ nhất quán với tên các file hiện có trong repo. Xem cấu trúc hiện tại trước khi đặt tên mới.

Tuyệt đối tránh:
- Hậu tố/tiền tố chung chung: helper, utils, common, misc, manager, handler, data, info, stuff, temp, new, final, v2, copy, test1.
- Tên dài lê thê ghép nhiều từ thừa (ví dụ: `evaluation_result_data_processing_helper_function.py`).
- Tên mang tính giải thích quá trình (`fixed_`, `updated_`, `improved_`, `claude_`, `ai_generated_`).
- Viết tắt khó hiểu hoặc tự chế.
- Số thứ tự vô nghĩa (`file1`, `script2`).

Trước khi tạo file mới, nếu tên chưa rõ ràng thì đề xuất 2-3 phương án tên và chọn cái tốt nhất, giải thích ngắn gọn lý do.

Áp dụng trong dự án này:
- Thư mục chứa Python package (có `__init__.py`) dùng snake_case vì Python không import được tên có dấu gạch ngang (ví dụ `ai_engine`, `test_cases`). Các thư mục còn lại dùng kebab-case.
- File React component dùng PascalCase (`DocumentsPage.jsx`); hook và module JS khác dùng camelCase (`useAuth.js`, `httpClient.js`).
- Tiền tố số trong `docs/` (`01_`, `02_`...) là thứ tự đọc có chủ đích, theo danh sách task M1; không dùng tiền tố số ở nơi khác.

Lưu ý
Mở một cuộc trò chuyện mới (hoặc một Project nếu bạn dùng) và dán toàn bộ Master Prompt vào làm bối cảnh gốc.
Gõ thêm: “Chỉ làm task tôi giao, mỗi lần một task, dừng lại chờ tôi duyệt trước khi sang task khác.”
Tạo thư mục docs/ trong repo và một file docs/progress_log.md để ghi lại kết quả sau mỗi task.

