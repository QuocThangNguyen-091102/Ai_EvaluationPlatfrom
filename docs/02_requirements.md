# 02. Người dùng mục tiêu và yêu cầu (M1-T02)

Trạng thái: bản nháp chờ duyệt. Mỗi yêu cầu có mã và cách kiểm chứng để dùng làm acceptance criteria ở các milestone sau.

## 1. Persona

| Mã | Persona | Mục tiêu | Dùng platform để |
|----|---------|----------|------------------|
| P1 | **LLM QA Engineer** (persona chính) | Biết một cấu hình RAG tốt hay kém, và kém ở đâu | Tạo dataset, chạy evaluation, phân tích từng case lỗi, so sánh các lần chạy |
| P2 | **RAG Developer** | Cải thiện chất lượng ứng dụng RAG | Thử các cấu hình (model, Top-K, prompt; đổi chunk size nằm ngoài MVP, xem `03_mvp_scope.md`) trên cùng dataset và so sánh chất lượng, độ trễ, chi phí |
| P3 | **Security Reviewer** | Biết ứng dụng LLM bị tấn công được những kiểu nào | Chạy bộ test Prompt Injection, Jailbreak, Data Leakage, Access Control, Malicious Documents trên ứng dụng thử nghiệm |
| P4 | **End User của ứng dụng RAG mẫu** | Hỏi đáp trên tài liệu của chính mình | Upload tài liệu, đặt câu hỏi, nhận câu trả lời kèm nguồn |

Ghi chú: ở giai đoạn đầu cả P1 đến P4 có thể là cùng một người (bạn). Việc tách persona giúp thiết kế phân quyền và giao diện rõ ràng.

## 2. Functional Requirements (FR)

Mức ưu tiên: **M** = Must-have cho MVP, **D** = Deferred (xem `03_mvp_scope.md`).

### Tài khoản

| Mã | Yêu cầu | Ưu | Cách kiểm chứng |
|----|---------|----|-----------------|
| FR-01 | User đăng ký và đăng nhập bằng email và mật khẩu | M | Test API: đăng ký, đăng nhập đúng và sai thông tin |
| FR-02 | Endpoint cần đăng nhập từ chối request không có token hợp lệ | M | Test API: gọi không token trả 401 |

### Ingestion

| Mã | Yêu cầu | Ưu | Cách kiểm chứng |
|----|---------|----|-----------------|
| FR-03 | Upload tài liệu PDF, DOCX, TXT; từ chối loại file hoặc dung lượng không hợp lệ với lỗi rõ ràng | M | Test upload file hợp lệ, sai loại, quá lớn |
| FR-04 | Hệ thống trích văn bản, làm sạch, chia chunk (kích thước và overlap cấu hình được), tạo embedding và lưu vector | M | Sau upload, DB có chunk và vector gắn đúng document_id |
| FR-05 | Mỗi document có trạng thái xử lý (uploaded, processing, ready, failed) và thông báo lỗi khi thất bại | M | Test với file hỏng: trạng thái failed kèm lý do, tiến trình không sập |
| FR-06 | Xem danh sách, xem chi tiết, xóa và reprocess document; upload trùng có hành vi xác định | M | Test xóa làm mất chunk và file gốc; reprocess không tạo chunk trùng |

### Chat / RAG

| Mã | Yêu cầu | Ưu | Cách kiểm chứng |
|----|---------|----|-----------------|
| FR-07 | User đặt câu hỏi và nhận câu trả lời dựa trên tài liệu của chính mình, kèm trích dẫn nguồn | M | Test end-to-end với tài liệu mẫu |
| FR-08 | Khi bằng chứng không đủ, hệ thống nói không đủ thông tin thay vì bịa | M | Test với câu hỏi không có đáp án trong tài liệu |
| FR-09 | Retrieval chỉ trả chunk thuộc tài liệu mà user được phép truy cập | M | Test user A không bao giờ nhận chunk của user B |
| FR-10 | Mỗi lượt hỏi lưu: chunk được truy xuất kèm điểm, model và cấu hình, latency, token, chi phí ước tính | M | Kiểm tra bản ghi trong DB sau một lượt hỏi |
| FR-11 | Lưu và xem lại session chat và message | M | Test API liệt kê session và message |

### Dataset và Evaluation

| Mã | Yêu cầu | Ưu | Cách kiểm chứng |
|----|---------|----|-----------------|
| FR-12 | Tạo dataset và version; version đã duyệt là bất biến, sửa thì tạo version mới | M | Test cố sửa version đã duyệt bị từ chối |
| FR-13 | Test case gồm: câu hỏi, ground-truth answer, reference contexts, nguồn, loại câu hỏi, độ khó, hành vi mong đợi | M | Kiểm tra schema, import có validate |
| FR-14 | Import và quản lý test case hàng loạt (CSV/JSON) | M | Test import file hợp lệ và sai định dạng |
| FR-15 | Chạy evaluation run gắn với một dataset version và một cấu hình; runner gọi đúng RAG pipeline của chat | M | Test runner và pipeline dùng cùng hàm; kiểm tra metadata run |
| FR-16 | Tính retrieval metrics: Precision@K, Recall@K, MRR, NDCG@K | M | Unit test với ví dụ tự tính tay |
| FR-17 | Tính ít nhất hai generation metric: Faithfulness và Answer Relevancy; ghi rõ judge model và prompt của judge | M | Chạy trên case mẫu, kiểm tra metadata judge |
| FR-17b | Tính thêm Context Precision và Context Recall | D | Chạy trên case mẫu, sau khi hai metric đầu đã được kiểm chứng với người |
| FR-18 | Lưu kết quả từng case và tổng hợp; một case lỗi không làm hỏng cả run | M | Test chèn một case gây lỗi, run vẫn hoàn tất |

### Security Testing

| Mã | Yêu cầu | Ưu | Cách kiểm chứng |
|----|---------|----|-----------------|
| FR-19 | Có test case bảo mật theo 5 nhóm: Prompt Injection, Jailbreak, Data Leakage, Access Control, Malicious Documents | M | Mỗi nhóm có ít nhất một test case hợp lệ theo schema |
| FR-20 | Security runner chạy test case qua cùng RAG pipeline, so sánh hành vi thực tế với mong đợi, gán pass/fail và severity, lưu evidence | M | Chạy bộ test, kiểm tra bản ghi kết quả |
| FR-21 | Báo cáo bảo mật có khuyến nghị giảm thiểu và nêu phần chưa được kiểm tra | M | Đọc báo cáo mẫu |

### Benchmark và Báo cáo

| Mã | Yêu cầu | Ưu | Cách kiểm chứng |
|----|---------|----|-----------------|
| FR-22 | So sánh ít nhất hai model hoặc cấu hình trên cùng dataset version, đo chất lượng, latency, token, chi phí ước tính | M | Một benchmark run có kết quả cho hai cấu hình |
| FR-23 | Xem lịch sử run và xuất kết quả CSV | M | File CSV khớp dữ liệu trong DB |
| FR-24 | Xuất báo cáo PDF | D | Xem `03_mvp_scope.md` |
| FR-25 | Dashboard tổng quan: document, chat, dataset, evaluation, security, benchmark | M | Mỗi trang gọi API đã tài liệu hóa, có trạng thái loading và lỗi |

## 3. Non-functional Requirements (NFR)

Các yêu cầu về hiệu năng và chi phí chưa có con số vì chưa có baseline; con số sẽ được đặt sau khi đo (theo Master Prompt, không đặt ngưỡng tùy ý).

| Mã | Nhóm | Yêu cầu | Cách kiểm chứng |
|----|------|---------|-----------------|
| NFR-01 | Bảo mật | Secret và API key chỉ nằm trong biến môi trường; không có trong code hay Git history | Quét repo trước mỗi gate; `.env` nằm trong `.gitignore` |
| NFR-02 | Bảo mật | Mật khẩu lưu dưới dạng hash; không ghi mật khẩu và dữ liệu nhạy cảm vào log | Review code và kiểm tra log mẫu |
| NFR-03 | Bảo mật | Cô lập dữ liệu theo user ở cả tầng API và tầng truy vấn vector | Test cô lập ở gate M3 và M4 |
| NFR-04 | Bảo mật | Frontend không kết nối trực tiếp DB và không chứa API key của provider | Review code frontend và cấu hình |
| NFR-05 | Tái lập | Mỗi run lưu dataset version, model và version, embedding model, prompt version, chunk size, overlap, Top-K, temperature, framework version, timestamp | Kiểm tra bản ghi run đủ trường |
| NFR-06 | Tái lập | Chạy lại với cùng cấu hình tái tạo được quy trình; phần ngẫu nhiên của LLM được ghi nhận, không giả định là xác định | Chạy lại run baseline, so sánh metadata và nêu độ chênh |
| NFR-07 | Độ tin cậy | Lỗi parsing, provider, rate limit, timeout, database được xử lý có kiểm soát (retry có giới hạn, ghi lỗi, không sập tiến trình) | Test với provider giả gây lỗi |
| NFR-08 | Hiệu năng | Ghi lại latency của từng lượt hỏi và từng run. Ngưỡng chấp nhận đặt sau khi có baseline | Có số đo trong DB |
| NFR-09 | Chi phí | Ghi token và chi phí ước tính cho mỗi lượt gọi; ghi rõ cách ước tính và thời điểm giá | Báo cáo benchmark nêu cách tính |
| NFR-10 | Kiến trúc | Chỉ một RAG pipeline dùng chung cho Chat, Evaluation, Benchmark, Security | Review code ở audit cuối (gate M9) |
| NFR-11 | Kiểm thử | Có unit, integration và end-to-end test cho các luồng chính | Test chạy xanh theo gate từng milestone |
| NFR-12 | Triển khai | Máy sạch chạy được toàn bộ stack bằng Docker Compose theo README | Thử trên máy sạch ở gate M2 và M9 |
| NFR-13 | Trung thực | Mọi con số trong báo cáo đến từ run thật; giới hạn của metric và của kiểm thử được ghi rõ | Rà soát báo cáo trước khi công bố |
| NFR-14 | Khả năng bảo trì | Module có ranh giới rõ (router, service, repository, AI engine); đặt tên theo quy ước ở `CLAUDE.md` | Review cấu trúc và tên file theo từng milestone |
| NFR-15 | Chi phí | Bản demo trên internet dùng hạ tầng miễn phí; chấp nhận giới hạn (ngủ, dung lượng, hạn mức). Chi tiết `11_free_deployment.md` | Triển khai thật và kiểm tra hoạt động ở M9-T04 |
| NFR-16 | Giao diện | Giao diện web tương tác cho mọi luồng chính (đăng nhập, tài liệu, chat, dataset, đánh giá, bảo mật, benchmark), dùng được trên trình duyệt máy tính | Mở từng trang và chạy luồng chính (E2E ở M9-T03) |
