# Progress Log

Ghi lại kết quả sau mỗi task. Mỗi task một mục, mới nhất ở trên cùng.
Mã task theo danh sách task: `M<milestone>-T<số>` (ví dụ M1-T01).

## Mẫu một mục

```
### M?-T?? | Tên task | YYYY-MM-DD
- Trạng thái: Hoàn thành / Đang làm / Cần sửa lại
- Đã làm gì:
- File tạo/sửa:
- Đã kiểm tra thế nào (lệnh, kết quả thật):
- Lỗi gặp phải:
- Học được gì:
- Việc tiếp theo (chờ user duyệt):
```

---

### M4-T02 | Retriever có kiểm soát quyền | 2026-11-06
- Trạng thái: Hoàn thành.
- File: `ai_engine/retrieval/metadata_filters.py` (`RetrievalScope` bắt buộc có `user_id`, `build_scope_filter`), `ai_engine/retrieval/vector_retriever.py` (`retrieve`), `tests/integration/test_vector_retriever.py`.
- Thiết kế: điều kiện `user_id` (trên cả chunk và document), trạng thái `ready` và bộ lọc tài liệu nằm trong câu SQL; mọi giá trị qua tham số; quét chính xác, chưa dùng chỉ mục gần đúng; không import backend, nhận session từ caller.
- Kiểm tra thật: 11 test pass, gồm user A hỏi đúng nội dung "canary" của user B mà không nhận được chunk nào của B, bộ lọc tài liệu không với tới tài liệu của người khác, chỉ tìm tài liệu `ready`.

### M3-T10 | GATE M3: Ingestion | 2026-11-06
- Trạng thái: **Đạt** (đóng sau khi làm trước M4-T01, M4-T03; xem mục ĐI TRƯỚC GATE).
- Điều kiện và bằng chứng: test unit và integration của ingestion xanh (239 backend, 53 giao diện); user A không thấy, sửa, xóa, xử lý lại tài liệu của user B (test 404 ở list, detail, delete, reprocess; chunk mang `user_id` của chủ và DB chặn sai chủ); manifest đã cập nhật.
- Trên stack Docker với model thật: PDF tiếng Việt và TXT dài xử lý tới `ready`; reprocess đổi kích thước chunk không tạo trùng; khởi động lại backend thì tài liệu dở thành `failed` kèm hướng dẫn và xử lý lại được.

### M3-T07 và M3-T08 (phần 2) | Ingestion chạy nền và xử lý lại | 2026-11-06
- Trạng thái: Hoàn thành (làm bằng Opus 5.5 theo quy tắc của user).
- File: `ai_engine/ingestion/ingestion_pipeline.py`; `backend/app/services/ingestion_service.py` (mới, đúng tên trong danh sách task), `repositories/chunk_repository.py`, `core/rag_defaults.py` (mới), `core/providers.py` (mới), `configs/rag_default.yaml` (nguồn duy nhất cho giá trị mặc định); route upload thêm tác vụ nền, route mới `POST /documents/{id}/reprocess`; `main.py` phục hồi lúc khởi động; `database/session.py` thêm `open_session` và thời gian chờ kết nối 10 giây; Docker copy `configs/`; giao diện có nút "Xử lý lại".
- Thiết kế: pipeline thuần trong `ai_engine` (không biết DB); service mở session riêng, đọc các trường cần trước khi commit để không giữ transaction trong lúc embed; thay chunk và đặt `ready` trong một transaction; mọi lỗi kết thúc bằng `failed` với lý do an toàn; xóa tài liệu giữa chừng thì bỏ qua êm; reprocess trả 409 khi đang xử lý. Mặc định 250 từ, chồng 50 (khoảng 300 token, dưới giới hạn 512).
- Kiểm tra thật: 239 test backend pass (27 test mới), 53 test giao diện pass; kiểm tra trên stack thật như ở gate.
- Giới hạn: tác vụ nền mất khi khởi động lại (đã có phục hồi); chỉ đúng với một tiến trình backend.
- Sự cố môi trường: Docker Desktop tự tắt thêm một lần; test treo 2 phút vì không có thời gian chờ kết nối, đã thêm.

### M4-T03 | Adapter LLM, prompt có phiên bản, ước tính chi phí, retry | 2026-11-06
- Trạng thái: Hoàn thành (chưa gọi LLM thật vì chưa chọn provider; mọi test dùng HTTP giả).
- File: `ai_engine/generation/base_llm_client.py` (interface, các loại lỗi), `openai_compatible_client.py` (đổi tên từ `openai_llm_client.py`: một adapter cho mọi API chuẩn OpenAI, gồm nhiều gói miễn phí và LLM chạy cục bộ), `prompt_templates.py` (phiên bản `rag-v1`), `cost_estimator.py`, `ai_engine/provider_retry.py`, `configs/models.yaml`; `requirements.txt` thêm `httpx`, `PyYAML`.
- Quyết định: chỉ retry lỗi tạm thời (timeout, 429 theo `Retry-After`, 5xx), không retry sai key; thông điệp lỗi không chứa API key hay nội dung prompt; prompt yêu cầu trích nguồn `[n]`, câu từ chối cố định khi thiếu thông tin, và coi nội dung tài liệu là dữ liệu chứ không phải chỉ dẫn (phòng prompt injection, chưa đo hiệu quả); chi phí không biết thì trả None, không trả 0.
- Kiểm tra thật: 28 test mới pass.

### M4-T01 | Bảng chat, ngữ cảnh truy xuất, cấu hình model | 2026-11-06
- Trạng thái: Hoàn thành (làm trước M4-T02 và T04 vì độc lập; gate M3 chưa đóng, xem mục "ĐI TRƯỚC GATE" ở dưới).
- File: `models/chat.py` (`ChatSession`, `ChatMessage`), `models/model_config.py`, `models/retrieved_context.py` (mới), migration `0003`, `tests/integration/test_chat_schema.py`.
- `ModelConfiguration` lưu: provider và model LLM, provider và model embedding, phiên bản prompt, `top_k`, `temperature`, `chunk_size`, `chunk_overlap`; có CHECK bảo vệ giá trị vô lý, tên duy nhất theo user. `RetrievedContext` lưu bản chụp nội dung chunk; hiện chỉ gắn với message chat, các cột gắn với evaluation và security thêm ở M6, M7.
- Kiểm tra thật: 188 test pass (16 test mới), `alembic check` khớp, downgrade rồi upgrade chạy sạch. **Đã kiểm chứng điều mình ghi là chưa kiểm chứng ở M2-T04**: RESTRICT chặn xóa cấu hình đang có message dùng; xóa chunk hoặc tài liệu thì ngữ cảnh truy xuất vẫn còn kèm bản chụp; xóa user kéo theo mọi dữ liệu dưới nó.

### ĐI TRƯỚC GATE | 2026-11-06
- M3-T07 (ingestion service) cần Opus 5.5 và user chưa đổi model, nên mình làm trước các task cơ bản độc lập ở M4 đến M6 để không chờ. Gate M3 chưa đóng; sẽ quay lại làm M3-T07, phần reprocess của T08 và gate khi có Opus. Hàng đợi cần Opus: M3-T07, M4-T02, M4-T04, M5-T04 (cần người viết dataset), M6-T03, M6-T04, M6-T07, M7-T04, M7-T06, M8-T03.

### M3-T09 | Giao diện: đăng nhập và trang Tài liệu | 2026-11-06
- Trạng thái: Hoàn thành giao diện. Cột trạng thái xử lý sẽ có ý nghĩa đầy đủ khi M3-T07 xong (hiện tài liệu dừng ở "Đã tải lên").
- Làm trước thứ tự một chút (cùng M3-T08 phần 1) theo yêu cầu của user: cần giao diện tương tác và có thể deploy miễn phí.
- File: `frontend/src/` gồm `main.jsx`, `App.jsx`, `styles.css`, `formatting.js`, `contexts/AuthContext.jsx`, `hooks/useAuth.js`, `components/ProtectedRoute.jsx`, `components/BackendStatus.jsx`, `layouts/MainLayout.jsx`, `pages/LoginPage.jsx`, `pages/DocumentsPage.jsx`, `services/api/{httpClient,authApi,documentApi}.js`; thêm `react-router-dom`, `vitest`, Testing Library.
- Tính năng: đăng nhập, đăng ký (lỗi 422 hiện lý do cụ thể), chuyển hướng về trang đang định vào, tự đăng xuất khi token hết hạn, tải lên nhiều file (kéo thả hoặc chọn), kiểm tra đuôi file trên giao diện (server vẫn là nơi quyết định), danh sách có phân trang, xóa có xác nhận, tự làm mới khi còn tài liệu đang xử lý (dừng sau 20 lần), trạng thái đang tải và lỗi, chế độ tối, thích ứng điện thoại.
- Quyết định: token lưu trong localStorage (giải thích rủi ro XSS trong code); backend kiểm tra mọi quyền, `ProtectedRoute` chỉ là tiện ích giao diện.
- Kiểm tra thật: 52 test giao diện pass (chạy 3 lần ổn định); `npm run build` OK; kịch bản trình duyệt thật (Chromium tự động) trên stack Docker: 13 kiểm tra pass (chuyển hướng, đăng nhập sai, đăng ký, upload hợp lệ và bị từ chối, trùng nội dung, tải lại giữ phiên, xóa, đăng xuất, đăng nhập lại), xem ảnh chụp bản sáng, tối, điện thoại.
- Lỗi tìm thấy bằng trình duyệt thật và đã sửa: trên điện thoại trang bị tràn ngang vì chữ ẩn trong tiêu đề cột nằm ngoài vùng cuộn của bảng (sửa bằng `position: relative` cho khung bảng). Test jsdom không thể bắt lỗi này.
- Chưa làm: các trang Chat, Dataset, Evaluation, Security, Benchmark; kiểm tra truy cập bàn phím và đọc màn hình đầy đủ; kiểm thử trên Safari và Firefox.

### M3-T08 (phần 1) | Danh sách, chi tiết, xóa tài liệu | 2026-11-06
- Trạng thái: phần 1 hoàn thành; **reprocess chưa làm** (phụ thuộc M3-T07).
- Endpoint: `GET /api/v1/documents` (lọc `status`, phân trang `limit` 1 đến 100, `offset`), `GET /api/v1/documents/{id}`, `DELETE /api/v1/documents/{id}`.
- Cô lập user: tài liệu của người khác hoặc không tồn tại đều trả cùng 404; xóa chỉ xóa bản ghi của chính user, chunk bị DB xóa theo, file xóa sau (nếu xóa file lỗi chỉ còn file thừa vô hại).
- Kiểm tra thật: 20 test mới pass, ổn định qua 3 lần chạy. Lỗi trong test của mình: các upload trong một test chung một transaction nên `now()` bằng nhau, thứ tự "mới nhất trước" lúc đó phụ thuộc id ngẫu nhiên (một test pass do may mắn); đã đặt giờ tạo rõ ràng.

### M3-T06 | Adapter embedding chạy cục bộ | 2026-11-06
- Trạng thái: Hoàn thành
- File: `ai_engine/embeddings/base_embedder.py` (interface `Embedder`, `EmbeddingError`, `InputTooLongError`), `ai_engine/embeddings/local_embedder.py` (`LocalEmbedder`); đóng gói: `backend/Dockerfile` (PyTorch bản CPU, context là thư mục gốc repo để thấy `ai_engine/`), `backend/Dockerfile.dockerignore`, `docker-compose.yml` (volume `models`), `requirements.txt` (`torch`, `sentence-transformers`).
- Thiết kế: hai hàm riêng cho đoạn tài liệu và câu hỏi (thêm tiền tố `passage: ` và `query: `); nạp model muộn một lần; vector chuẩn hóa; kiểm tra token thật và **từ chối** đoạn vượt 512 token thay vì để model cắt âm thầm; kiểm tra số chiều khớp cấu hình ngay khi nạp; mọi lỗi thành `EmbeddingError` với thông điệp không chứa nội dung văn bản. Không dùng `provider_retry` vì model chạy cục bộ không có lỗi mạng.
- Kiểm tra thật: 12 test với model giả pass; 5 test với **model thật** pass (`RUN_MODEL_TESTS=1`): vector đúng 384 chiều khớp cột database, xếp hạng tiếng Việt đúng, vector chuẩn hóa và ổn định, tiền tố làm vector khác nhau, đoạn dài bị từ chối. Chạy model thật trong container: RAM khoảng 933 MB, image 2,2 GB, 32 đoạn trong 0,22 giây.
- Sự cố: tải PyTorch bị ngắt mạng và đường dẫn Windows quá dài làm cài đặt lỗi; đã xử lý bằng đường dẫn ngắn và thử lại.

### YÊU CẦU MỚI | Giao diện tương tác và triển khai miễn phí | 2026-11-05
- User yêu cầu: có giao diện tương tác, chạy được trên internet, hoàn toàn miễn phí, và giao quyền tự làm.
- Đã tra điều khoản hiện tại của Vercel, Neon, Supabase và các nơi chạy container miễn phí (nhiều nguồn thứ cấp mâu thuẫn nhau). Kết luận và kế hoạch ở `docs/11_free_deployment.md`: Vercel chỉ cho giao diện; backend cần nơi chạy container đủ RAM; chọn nơi cụ thể và kiểm tra lại điều khoản ở M9-T04. Số đo thật về RAM và image đã ghi vào tài liệu đó.
- Việc chỉ user làm được: tạo tài khoản các dịch vụ, đưa secret vào bảng cấu hình, bấm triển khai.

### M3-T05 | Làm sạch văn bản + chunker | 2026-11-05
- Trạng thái: Hoàn thành
- File: `ai_engine/ingestion/text_cleaner.py` (`clean_text`, `clean_document`), `ai_engine/chunking/fixed_size_chunker.py` (`chunk_document`, `full_text`); test: `unit/test_text_cleaner.py`, `unit/test_chunker.py`.
- Làm sạch: chuẩn hóa NFC cho chữ có dấu, bỏ ký tự vô hình và ký tự điều khiển, gộp khoảng trắng, chuẩn hóa xuống dòng. **Không nối dòng bị ngắt và không bỏ gạch nối cuối dòng** (đổi so với dự định lúc đọc PDF: nối bừa làm mất cấu trúc DOCX và vị trí ký tự).
- Chunker: kích thước và overlap tính bằng **từ** (cấu hình được; kiểm tra `0 <= overlap < chunk_size`). Mỗi chunk có `index`, `content`, `page_number` (trang của từ đầu), `char_start`, `char_end`, `word_count`; `full_text[char_start:char_end] == content` (có test).
- Kiểm tra thật: 140 test pass (47 integration cần DB và 93 unit), gồm một test chạy PDF tiếng Việt thật qua parse, làm sạch và chia chunk.
- Lưu ý cho M3-T06 và M5: (1) embedder phải đếm token thật vì model cắt âm thầm quá 512 token; (2) vị trí ký tự của chunk tính trên văn bản đã làm sạch, nên tham chiếu `reference_contexts` ở M5 chỉ ổn định khi parser và bộ làm sạch không đổi phiên bản.
- Sự cố: lệnh commit của mình bị ngắt giữa chừng, mình kiểm tra lại trạng thái thật rồi mới commit.

### M3-T04 | Parsers TXT / PDF / DOCX | 2026-11-05
- Trạng thái: Hoàn thành
- File: `ai_engine/ingestion/txt_parser.py`, `pdf_parser.py`, `docx_parser.py`; mới: `ai_engine/ingestion/parsed_document.py` (kiểu dữ liệu chung và `ParsingError`); `backend/tests/unit/test_parsers.py`, `backend/tests/fixtures/vi_two_pages.pdf`; sửa `backend/pytest.ini` (thêm thư mục gốc repo vào đường dẫn import), `requirements.txt` (`pypdf`, `python-docx`).
- File hỏng, PDF có mật khẩu, PDF không có văn bản, DOCX nén bất thường đều ném `ParsingError` với thông điệp an toàn (không chứa nội dung file), không làm sập tiến trình.
- Kiểm tra thật: 110 test pass (17 test mới). PDF mẫu tiếng Việt thật (tạo bằng font Arial có dấu) trích đúng chữ có dấu theo từng trang.
- Phát hiện: PDF xuống dòng theo bố cục trang nên một câu bị ngắt thành hai dòng ("chấp / thuận"); bước làm sạch (M3-T05) phải nối lại.
- Giới hạn đã biết: PDF dạng ảnh quét không có văn bản (không OCR); DOCX không đọc header, footer, chú thích cuối trang, hộp văn bản, bảng lồng nhau. Chưa thử với PDF thực tế phức tạp (nhiều cột, bảng): chất lượng trích phụ thuộc từng file.
- Lưu ý đóng gói: thư mục `ai_engine/` nằm ngoài `backend/` nên Docker build context hiện tại chưa thấy nó; sẽ sửa khi backend bắt đầu import `ai_engine` (M3-T07).

### M3-T03 | Upload endpoint + validation + lưu file gốc | 2026-11-05
- Trạng thái: Hoàn thành
- File mới: `core/file_validation.py`, `core/file_storage.py` (đã có trong manifest, chuyển từ Planned), `repositories/document_repository.py`, `schemas/document.py`, `services/document_service.py`, `api/routes/documents.py`; sửa `core/config.py` (`upload_dir`, `max_upload_size_mb`), `api/dependencies.py`, `main.py`, `Dockerfile` (thư mục upload thuộc `appuser`), `docker-compose.yml` (volume `uploads`), `requirements.txt` (`python-multipart`), `.env.example`; test: `unit/test_file_validation.py`, `integration/test_document_upload_api.py`, `conftest.py` (fixture `make_authenticated_user`).
- Endpoint: `POST /api/v1/documents` (multipart): 202 (status `uploaded`), 409 kèm `existing_document_id`, 413, 415, 422, 401.
- Quyết định kỹ thuật: nhận diện loại file bằng nội dung (PDF phải bắt đầu `%PDF-`; DOCX phải là zip có `word/document.xml`; TXT phải là UTF-8, bỏ qua `Content-Type` do client gửi); tên file trên đĩa do server tạo (`<user_id>/<document_id><đuôi>`), tên client chỉ để hiển thị và đã làm sạch; kiểm tra dung lượng khi đọc theo từng phần nên dừng sớm khi vượt giới hạn; ghi file nguyên tử (ghi `.part` rồi đổi tên); lưu DB và lưu file đi cùng nhau: ghi file lỗi thì rollback và không để lại bản ghi hay file mồ côi; trùng nội dung phát hiện bằng SHA-256 theo từng user.
- Kiểm tra thật: 93 test pass (45 unit, 48 integration). Test không để lại dữ liệu trong DB. Trên stack Docker thật qua HTTP: TXT 202, trùng 409 (đúng id cũ), PDF giả 415, file 22 MB 413, không token 401; file nằm trong volume `uploads` thuộc `appuser`. Đã dọn dữ liệu thử.
- Lỗi gặp và đã sửa: (1) file TXT mã hóa UTF-16 bị báo "nhị phân" gây hiểu nhầm, đã sửa code để báo yêu cầu UTF-8; (2) hai lỗi trong test của mình khi tạo dữ liệu cp1258.
- Rủi ro mới: R20 (server vẫn nhận hết file quá lớn trước khi từ chối, cần giới hạn ở reverse proxy trước khi mở ra Internet), R21 (xem kết quả thử model).
- Chưa làm: parse nội dung (M3-T04), xử lý nền (M3-T07), list, chi tiết, xóa, reprocess (M3-T08).
- File TXT chỉ nhận UTF-8: file Windows-1258 hoặc UTF-16 bị từ chối kèm thông báo rõ ràng; có thể nới sau nếu cần.

### M3-T02 | Authentication (register, login, me) | 2026-11-05
- Trạng thái: Hoàn thành
- File: `core/security.py`, `core/config.py` (thêm `jwt_secret`, `jwt_expire_minutes`, `password_min_length`), `core/exceptions.py` (thêm `headers` cho `AppError`), `repositories/user_repository.py`, `schemas/auth.py`, `services/auth_service.py`, `api/dependencies.py`, `api/routes/auth.py`, `main.py`, `docker-compose.yml` (truyền `JWT_SECRET`), `requirements.txt` (thêm `PyJWT`, `argon2-cffi`, `email-validator`), `.env.example`, `README.md`; test: `unit/test_security.py`, `unit/test_auth_schemas.py`, `integration/test_auth_api.py`, `conftest.py` (fixture `api_client`).
- Endpoint: `POST /api/v1/auth/register` (201, 409, 422), `POST /api/v1/auth/login` (200, 401), `GET /api/v1/auth/me` (200, 401), đúng hợp đồng `08_api_contracts.md`.
- Quyết định kỹ thuật: băm mật khẩu bằng argon2 (không giới hạn 72 byte như bcrypt); JWT HS256 chỉ nhận đúng thuật toán (từ chối `alg: none`); email chuẩn hóa chữ thường; đăng nhập sai trả cùng một thông báo và có bước tốn thời gian băm giả khi email không tồn tại (giảm dò email qua thời gian phản hồi); mỗi request kiểm tra lại `is_active` trong DB nên user bị khóa mất hiệu lực ngay; Service không truy cập DB, chỉ qua `UserRepository`.
- Kiểm tra thật: 53 test pass (24 unit, 29 integration); unit test chạy được cả khi không có `.env`; test không để lại dữ liệu trong DB (đếm user sau test = 0). Trên stack thật qua HTTP: đăng ký 201, đăng ký trùng 409, đăng nhập sai 401, đăng nhập đúng nhận token, `/auth/me` có token trả đúng user, không token trả 401 kèm `WWW-Authenticate: Bearer`, CORS cho origin của frontend đúng. Đã xóa user thử nghiệm.
- Lỗi gặp: một test của mình dùng chữ tiếng Việt trong giá trị header HTTP (phải là ASCII); đã sửa test, không phải code ứng dụng.
- Rủi ro mới ghi vào `10_test_risk_learning.md`: R18 (chưa giới hạn số lần thử đăng nhập, chấp nhận cho MVP chạy cục bộ nhưng phải xử lý trước khi mở ra Internet), R19 (JWT không thu hồi tức thì).
- Chưa làm: giao diện đăng nhập (M3-T09); giới hạn tần suất đăng nhập; chưa thử trên trình duyệt thật.

### DUYỆT | Gate M1 và M2 | 2026-11-05
- User duyệt gate Milestone 1 và Milestone 2 bằng tin nhắn "Duyệt" (sau khi mình trả lời câu hỏi "Duyệt ở đâu" và nêu các điểm còn tồn tại: giao diện chưa kiểm tra bằng trình duyệt thật, repo chưa có remote).
- Các điểm user chưa trả lời, vẫn còn mở: remote GitHub và push, cảnh báo `httpx`/`httpx2`.

### M3-T01 | Models + migration: users, documents, document_chunks | 2026-11-05
- Trạng thái: Hoàn thành
- File mới/sửa: `app/models/user.py`, `document.py`, `document_chunk.py`, `models/__init__.py`, `migrations/env.py` (import models), `migrations/versions/0002_create_users_documents_chunks.py`, `requirements.txt` (thêm `pgvector==0.5.1`), `alembic.ini` (bỏ cảnh báo `path_separator`), `tests/conftest.py` (fixture `migrated_database`, `db_session`), `tests/integration/test_ingestion_schema.py`. Đổi tên file rỗng `openai_embedder.py` thành `local_embedder.py`.
- Thiết kế đáng chú ý:
  - Khóa ngoại kép `(document_id, user_id)` trỏ tới `documents(id, user_id)`: DB từ chối chunk có `user_id` khác chủ của document. Đây là cách thực thi cho việc denormalize `user_id` đã quyết định ở M1.
  - Chưa tạo chỉ mục vector (xem lý do trong `07_database.md`); các chỉ mục thường đã có.
  - `status` dùng CHECK constraint thay vì ENUM của PostgreSQL để migration sau dễ sửa.
- Kiểm tra thật: `alembic upgrade head` OK; `alembic check` báo "No new upgrade operations detected" (model khớp DB); `downgrade base` rồi `upgrade head` OK; 20 test pass (13 test mới); backend container healthy với các model mới.
- 13 test mới kiểm tra: bảng tồn tại, cột vector đúng `vector(384)`, chỉ mục tồn tại, vector sai số chiều bị từ chối, chunk không thể mang `user_id` khác chủ document, cùng nội dung bị từ chối với cùng user nhưng cho phép khác user, email duy nhất, status mặc định và bị chặn giá trị lạ, xóa document xóa chunk, xóa user xóa document và chunk, thứ tự chunk duy nhất, truy vấn khoảng cosine trả chunk gần nhất trước.
- Chưa kiểm chứng: hành vi RESTRICT của PostgreSQL khi xóa user vẫn chưa kiểm chứng vì chưa có bảng nào dùng RESTRICT (các bảng đó đến ở M4 trở đi).

### M3 (điều kiện vào) | Chốt embedding chạy cục bộ | 2026-11-05
- User chọn phương án A3. Model: `intfloat/multilingual-e5-small`; thông số đọc từ cấu hình chính thức trên Hugging Face: 384 chiều, 512 token, giấy phép MIT, có tiếng Việt trong danh sách ngôn ngữ, bắt buộc tiền tố `query: ` và `passage: `.
- **Chạy thử model thật: đã làm (cùng ngày, sau lần đầu thất bại).** Lần đầu cài PyTorch bị ngắt mạng, lần hai lỗi vì đường dẫn Windows quá dài; lần ba dùng đường dẫn ngắn thì thành công. Kết quả thật: vector 384 chiều (`float32`); xếp hạng đúng ca tiếng Việt (0,914 so với 0,766); **truy xuất chéo ngôn ngữ yếu** (câu hỏi tiếng Việt với đoạn tiếng Anh đúng nghĩa chỉ 0,773); điểm cosine bị nén ở 0,77 đến 0,91; văn bản dài hơn 512 token bị cắt âm thầm; 32 đoạn ngắn embed trong 0,37 giây. Thử rất nhỏ (1 câu hỏi, 3 đoạn), chỉ kiểm tra model chạy và số chiều, không phải đo chất lượng. Chi tiết trong `06_deployment_tech.md`.
- Một điều chỉnh lời nói trước đó: mình từng nói quên tiền tố `query:`/`passage:` sẽ làm chất lượng "tụt âm thầm"; ở một ví dụ, bỏ tiền tố không làm khoảng cách điểm tệ hơn, nên tác hại này chưa được chứng minh. Vẫn giữ tiền tố theo khuyến cáo của tác giả model.
- Ghi chú: thư viện `huggingface-hub` kéo theo gói `httpx2` làm dependency, nên `httpx2` là gói có thật và được dùng bởi một thư viện lớn. Mình vẫn chưa thêm nó vào dự án (chỉ nằm trong môi trường thử tạm); quyết định xử lý cảnh báo của pytest vẫn để bạn.
- Tài liệu đã cập nhật: `06_deployment_tech.md` (mục 4, kèm giả định yếu), `07_database.md`, `09_repo_manifest.md`, `10_test_risk_learning.md`, `.env.example` (bỏ `EMBEDDING_API_KEY`).

---

### M2-T08 | GATE M2: Foundation | 2026-11-05
- Trạng thái: **Đạt, kèm 2 điểm cần user biết** (xem cuối mục).
- Cách kiểm tra: clone repo sạch vào thư mục tạm, làm đúng theo README (tạo `.env` với mật khẩu mới, `docker compose up --build -d`), rồi kiểm tra; sau đó dọn clone và volume của nó.
- Kết quả thật của bản clone sạch:
  - `docker compose ps`: db, backend, frontend đều `healthy`.
  - `GET /health` trả `{"status":"ok","database":"ok"}`; frontend trả HTTP 200.
  - Backend log có `Running upgrade -> 0001, enable pgvector extension`; DB mới có extension `vector` và `alembic_version = 0001`.
  - `pytest` theo README: 7 passed (6 unit, 1 integration); chỉ unit: 6 passed.
- Kiểm tra khác trong M2: dữ liệu DB còn sau `down` rồi `up` (M2-T03); `alembic downgrade base` rồi `upgrade head` chạy sạch (M2-T04); `/health` trả 503 khi dừng db và tự phục hồi khi db trở lại (M2-T05); backend chạy bằng user không phải root.
- Lỗi tìm thấy và đã sửa trong gate: `tests/conftest.py` đặt `DATABASE_URL` mặc định bằng biến môi trường nên ghi đè mật khẩu trong `.env`. Sửa ở commit `fix(tests)`; xác nhận bằng chạy pytest trong bản clone dùng mật khẩu khác.
- Quét Git history tìm secret: không có file `.env`, không có mẫu API key hay private key. **Đã xử lý sau gate:** một mật khẩu dev cục bộ (không phải secret thật, DB chỉ bind `127.0.0.1`) từng nằm trong 2 commit cũ của `conftest.py`. Vì repo chưa có remote, mình đã viết lại lịch sử để thay chuỗi đó bằng `DEV_PASSWORD_REDACTED` trong mọi commit (có sao lưu bundle ngoài repo trước khi làm, đã so khớp nội dung với bản cũ rồi xóa bản sao lưu). Kiểm tra sau đó: 0 chỗ còn chuỗi cũ trong toàn bộ lịch sử; 6 unit test pass. Mã commit của các commit sau M2-T05 đã đổi do viết lại lịch sử.
- **Điểm 2:** commit đầu chưa được push vì chưa có remote GitHub; cần user tạo repo và cung cấp địa chỉ.
- Chưa kiểm tra được: giao diện trên trình duyệt thật (chỉ kiểm tra HTTP 200 và CORS bằng curl); chạy trên máy khác (chỉ thử trên máy này bằng clone sạch).
- Manifest đã cập nhật: 18 file chuyển sang Implemented hoặc Tested, thêm 10 file mới của M2.

### M2-T07 | Logging, xử lý lỗi chuẩn, thiết lập pytest | 2026-11-05
- Trạng thái: Hoàn thành
- File: `core/logging.py`, `core/exceptions.py`, `core/config.py` (thêm `log_level`), `main.py`, `tests/conftest.py`, `tests/unit/test_health.py`, `tests/unit/test_error_handling.py`, `tests/integration/test_health_database.py`; mới: `pytest.ini`, `requirements-dev.txt`.
- Lỗi trả về theo một định dạng thống nhất `{"error":{"code","message","details"}}`; lỗi không lường trước trả 500 mà không lộ chi tiết nội bộ (có test).
- Kiểm tra: `pytest` 7 passed; `-m "not integration"` 6 passed.
- Lưu ý: pytest cảnh báo deprecation của `starlette.testclient` khi dùng `httpx` và gợi ý gói `httpx2`. Mình **không cài** gói đó vì chưa kiểm chứng gói này; test vẫn pass với `httpx==0.28.1`. Cần user quyết định có xử lý cảnh báo hay không.

### M2-T06 | Frontend skeleton | 2026-11-05
- Trạng thái: Hoàn thành
- File: `package.json`, `package-lock.json`, `index.html`, `vite.config.js`, `src/main.jsx`, `src/App.jsx`, `src/services/api/httpClient.js`, `Dockerfile`; mới: `src/services/api/healthApi.js`, `frontend/.dockerignore`; compose có thêm service `frontend`.
- Kiểm tra: `npm run build` thành công; container healthy; trang trả 200; API chấp nhận origin `http://localhost:5173`; `VITE_API_BASE_URL` lấy từ biến môi trường.
- Chưa kiểm tra bằng trình duyệt thật.

### M2-T05 | Backend Dockerfile + service backend | 2026-11-05
- Trạng thái: Hoàn thành
- File: `backend/Dockerfile`, `docker-compose.yml`, `app/api/routes/health.py`; mới: `backend/.dockerignore`.
- `/health` kiểm tra DB (trả 503 khi lỗi). Migration chạy khi container khởi động. Backend chạy bằng `appuser`.
- Kiểm tra: build và `up` thành công; 200 khi db chạy, 503 khi db dừng, 200 lại khi db trở lại.

### M2-T04 | Kết nối DB + Migration | 2026-11-05
- Trạng thái: Hoàn thành
- File: `app/database/session.py`, `base.py`, `migrations/env.py`, `script.py.mako`, `versions/0001_enable_pgvector_extension.py`, `alembic.ini`, `core/config.py` (thêm `database_url`).
- Kiểm tra: `alembic upgrade head` OK; `SELECT 1` qua session ứng dụng OK; extension `vector` 0.8.7 hoạt động; downgrade rồi upgrade lại OK.
- Lỗi gặp: dùng `localhost` làm chậm 5 giây mỗi kết nối vì Windows thử IPv6 trước trong khi cổng chỉ bind IPv4; đổi sang `127.0.0.1` trong `.env.example`.
- Chưa kiểm chứng: hành vi RESTRICT của PostgreSQL khi xóa user (mục 12 của báo cáo rà soát), sẽ kiểm chứng khi có migration cho các bảng.

### M2-T03 | Docker Compose + PostgreSQL/pgvector | 2026-11-05
- Trạng thái: Hoàn thành
- File: `docker-compose.yml`. Image `pgvector/pgvector:pg16`, volume `pgdata`, healthcheck `pg_isready`, cổng chỉ bind `127.0.0.1`.
- Kiểm tra: db healthy; tạo bảng, ghi dữ liệu, `docker compose down` rồi `up`, dữ liệu vẫn còn. Đã sửa `06_deployment_tech.md` cho khớp việc công bố cổng db ở `127.0.0.1`.
- Chuẩn bị: Docker Desktop chưa chạy lúc đầu, mình khởi động nó.

### M2-T02 | Backend skeleton + /health | 2026-11-05
- Trạng thái: Hoàn thành
- File: `requirements.txt` (pin phiên bản), `app/core/config.py`, `app/api/routes/health.py`, `app/main.py`.
- Kiểm tra: chạy uvicorn, `GET /health` trả 200; CORS preflight cho origin của frontend đúng.

### M2-T01 | Khởi tạo Git repository | 2026-11-05
- Trạng thái: Hoàn thành một phần: **chưa push** vì chưa có remote GitHub.
- File: `.gitignore`, `.env.example`, `README.md`. Đã `git init`, nhánh `main`, quy ước commit và branch ghi trong README.
- Kiểm tra: `.env` bị ignore (`git check-ignore`), không có `.env` trong danh sách file được theo dõi.

---

### M1-T11 | GATE M1: rà soát và duyệt thiết kế | 2026-11-05
- Trạng thái: Hoàn thành. Số mâu thuẫn còn lại theo kết quả rà soát: 0 trong các mục đã xác nhận.
- Cách làm: một agent độc lập đọc lại `docs/01` đến `docs/10` và `CLAUDE.md` rồi báo 26 mục (2 HIGH, 9 MEDIUM, 15 LOW). Mình đối chiếu lại các mục chính với văn bản thật trước khi sửa. Mình cũng tự kiểm tra đường dẫn trong manifest với cây thư mục thật.
- Đã sửa (các mục chính):
  - Runner (`evaluation`, `security`) không gọi Repository; Service truyền callback lưu kết quả. Sửa 04, 05, 09.
  - MVP làm 2 generation metric (Faithfulness, Answer Relevancy); Context Precision và Context Recall là Deferred (FR-17b). Sửa 02, 03.
  - Benchmark MVP chỉ đổi `llm_model`, `top_k`, `prompt_version`; API trả 422 với giá trị khác. Sửa 02, 04, 06, 07, 08.
  - Báo cáo CSV sinh tức thì, không lưu file; bảng `reports` chỉ là lịch sử xuất. Sửa 04, 07, 08, 09.
  - Điều kiện vào M3-T01: gọi thử provider để chốt embedding model và số chiều vector. Sửa 01, 06, 10.
  - Ngoại lệ có chủ đích cho `vector_retriever.py` và `/health`. Sửa 04, 09, 10.
  - `POST /chat/messages`, trạng thái ban đầu `pending`, HTTP thay cho HTTPS ở MVP, tên tham số lệch giữa 05 và 08, chữ "đề xuất" lỗi thời.
  - Bổ sung: bảng cascade, enum status cho security và benchmark run, endpoint của Dashboard và Security page, các file docs Planned, file Alembic, R9 mở rộng cho security và benchmark run.
- Chưa sửa: mục 21 phần "package marker" chỉ ghi chú trong manifest (thêm `__init__.py` khi tạo file đầu tiên); mục 12 về hành vi RESTRICT của PostgreSQL là suy luận chưa thử, sẽ kiểm chứng khi viết migration.
- Lưu ý gate: danh sách task yêu cầu user xác nhận "được phép bắt đầu code". Mình coi yêu cầu "Tiếp tục 10 task" của user là xác nhận cho các task M2.

---

### M1-T10 | Chiến lược test, rủi ro, lộ trình học | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/10_test_risk_learning.md`
- Nội dung: 3 tầng test và bảng test theo module, chiến lược tích hợp, rủi ro kỹ thuật R9 đến R17, lộ trình học M1 đến M9, gate đo được cho M2 đến M9. Không có ngưỡng điểm tự đặt.

### M1-T09 | Cây thư mục repo + File manifest | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/09_repo_manifest.md`
- Đã xóa 4 file rỗng đầu cơ (`base_chunker.py`, `recursive_chunker.py`, `configs/app.yaml`, `scripts/init_db.sh`) và thư mục `docs/diagrams/` (9 file `.mmd` rỗng, sơ đồ nằm trong các tài liệu md).
- Đã thêm vào manifest 14 file Planned (chưa tạo): ví dụ `model_configs.py`, `retrieved_context.py`, `file_storage.py`, `rag_config.py`, `rag_result.py`, `provider_retry.py`.
- Có bảng manifest đủ cột (trách nhiệm, phụ thuộc, dùng bởi, input, output, trạng thái, milestone) và quy tắc phụ thuộc giữa thư mục.

### M1-T08 | Đặc tả API | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/08_api_contracts.md`
- Nội dung: quy ước chung, định dạng lỗi thống nhất, luồng Router tới Response, 8 nhóm endpoint (thêm nhóm `/model-configurations` ngoài danh sách Master Prompt), ánh xạ trang giao diện tới endpoint.

### M1-T07 | Thiết kế Database + ER diagram | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/07_database.md`
- Nội dung: đúng 18 entity của Master Prompt, ERD Mermaid, cách vector gắn với chunk, quy tắc cô lập user, bảng cascade, 3 điểm cần quyết định (denormalize `user_id` ở chunk, benchmark đổi chunking, bất biến version).
- Kiểm tra: chưa render Mermaid.

### M1-T06 | Deployment diagram + rà soát Technology Stack | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt (đã chọn A1, đổi được trước M3-T01)
- File: `docs/06_deployment_tech.md`
- Nội dung: Deployment diagram, bảng service, volume, biến môi trường; bảng công nghệ gắn nhãn Essential, Optional, Unnecessary; 3 phương án provider (đã chọn A1); quyết định B (Ragas và DeepEval) hoãn tới M6-T04.
- Kiểm tra: chưa render Mermaid. Tên model, giá, phiên bản thư viện chưa được xác minh, sẽ xác minh khi cài.

---

### M1-T05 | Sơ đồ Sequence (4 luồng) | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/05_sequences.md`
- Nội dung: 4 sequence diagram (Ingestion, RAG, Evaluation, Security), bảng điểm tái sử dụng RAG Pipeline, hành vi retry, lỗi, upload trùng, xóa, reprocess, bảng đối chiếu mục 5.1 đến 5.4.
- Kiểm tra: chưa render Mermaid (chưa có công cụ render trong môi trường), mới tự đọc lại cú pháp. Cần xem thử trên preview Markdown của VS Code.
- Điểm mở: quy tắc cascade khi xóa document còn chốt ở M1-T07; cơ chế xử lý run bị kẹt khi backend khởi động lại chốt ở M3 và M6.

### M1-T04 | Kiến trúc tổng thể + 3 sơ đồ đầu | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/04_architecture.md`
- Nội dung: System Context, Container, Component (Mermaid flowchart); bảng module logic và đơn vị triển khai; bảng mô tả đủ 7 module theo 8 mục (responsibility, vị trí, input/output, dependency, caller/callee, storage, failure handling, tests); 3 quyết định đã chọn kèm lý do (chạy nền, file storage, user chạy evaluation/security).
- Kiểm tra: chưa render Mermaid, xem như trên.

### M1-T03 | Định nghĩa MVP thực tế | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/03_mvp_scope.md`
- Nội dung: câu trả lời "MVP xong thì demo được gì", Must-have, Deferred, Out-of-scope, workflow chính, 10 acceptance criteria.

### M1-T02 | Người dùng mục tiêu và yêu cầu | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/02_requirements.md`
- Nội dung: 4 persona, 25 FR (FR-01 đến FR-25), 14 NFR (NFR-01 đến NFR-14), mỗi yêu cầu có cách kiểm chứng. NFR hiệu năng và chi phí chưa có số vì chưa có baseline.

### M1-T01 | Đánh giá tính khả thi và giá trị portfolio | 2026-11-05
- Trạng thái: Hoàn thành bản nháp, chờ duyệt
- File: `docs/01_feasibility.md`
- Nội dung: kết luận nên làm có điều kiện, giá trị, độ phức tạp theo phần, 8 rủi ro (R1 đến R8) kèm cách giảm thiểu, các điều chưa biết.

---

### NAMING | Áp dụng quy ước đặt tên | 2026-11-05
- Trạng thái: Hoàn thành
- Đã làm gì: thêm mục 8 "Quy ước đặt tên" vào `CLAUDE.md`; đổi tên các file vi phạm quy ước.
- Đổi tên: `scripts/seed_demo_data.py` → `seed_demo.py`; `docs/SESSION_NOTES.md` → `session_notes.md`; 10 file trong `docs/` đổi theo tên của danh sách task M1 (ví dụ `06_file_manifest.md` → `09_repo_manifest.md`).
- Xóa: `frontend/src/utils/` (tên chung chung, thư mục rỗng); `docs/08_learning_roadmap.md` và `docs/10_risks_and_decisions.md` (gộp vào `10_test_risk_learning.md`).
- Thêm: `docs/03_mvp_scope.md` (file rỗng, có trong danh sách task M1).
- Đã kiểm tra thế nào: `ls` thư mục `docs/`, `scripts/`, `frontend/src/`; `grep` các đường dẫn cũ trong `CLAUDE.md` và `docs/`.

---

### SETUP | Chuẩn bị môi trường làm việc | 2026-11-05
- Trạng thái: Hoàn thành
- Đã làm gì: tạo bộ khung repo `ai-evaluation-platform/` (173 file rỗng, 52 thư mục), tạo `CLAUDE.md` chứa các ràng buộc dự án, tạo `docs/session_notes.md` và file log này.
- File tạo/sửa: `CLAUDE.md`, `docs/session_notes.md`, `docs/progress_log.md`, các file rỗng theo cây thư mục.
- Đã kiểm tra thế nào: liệt kê thư mục bằng `ls`/`find` để xác nhận file tồn tại. Chưa có code nên chưa có test.
- Lỗi gặp phải: không có.
- Học được gì: không có.
- Việc tiếp theo: chờ user giao task đầu tiên (dự kiến M1-T01).
