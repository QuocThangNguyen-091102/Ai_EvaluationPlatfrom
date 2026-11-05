# 01. Đánh giá tính khả thi và giá trị portfolio (M1-T01)

Trạng thái: bản nháp chờ duyệt. Đây là đánh giá định tính dựa trên Master Prompt, chưa có số đo thực tế nào.

## 1. Kết luận

**Nên làm, với điều kiện giữ MVP nhỏ và đi đúng thứ tự milestone.**

Dự án khả thi cho một người làm một mình vì mọi thành phần đều dùng công nghệ phổ biến (FastAPI, React, PostgreSQL + pgvector, Docker Compose). Phần khó không nằm ở công nghệ mà ở ba chỗ: chất lượng dataset đánh giá, độ tin cậy của metric, và việc giữ phạm vi trong tầm kiểm soát.

## 2. Giá trị thực tế

- Phần lớn tutorial RAG dừng ở "hỏi đáp chạy được". Dự án này đi tiếp sang câu hỏi mà đội làm sản phẩm AI thật sự gặp: hệ thống này tốt đến mức nào, so với cấu hình khác thì sao, có bị tấn công được không.
- Đánh giá RAG, đo hallucination và kiểm thử bảo mật cho ứng dụng LLM là những công việc có nhu cầu thật (LLM QA, AI Security). Dự án luyện đúng các kỹ năng này.
- Nền tảng Information Security của bạn là lợi thế: phần Security Testing là chỗ bạn có thể làm sâu hơn người chỉ có nền ML.

## 3. Mức phù hợp làm portfolio AI Engineer

| Tiêu chí | Đánh giá |
|----------|----------|
| Thể hiện tư duy kỹ thuật | Cao: có kiến trúc, DB, API, test, Docker, không chỉ là script. |
| Khác biệt so với dự án phổ biến | Cao: trọng tâm là evaluation và security, không phải chatbot. |
| Dễ trình bày | Trung bình: cần demo kịch bản rõ (upload, hỏi, chạy evaluation, xem báo cáo). |
| Rủi ro bị đánh giá là "quá rộng" | Trung bình: giảm bằng MVP chặt (xem `03_mvp_scope.md`). |
| Giá trị chỉ có khi có số liệu thật | Đúng: portfolio chỉ thuyết phục nếu mọi con số đến từ run thật và nêu rõ giới hạn. |

## 4. Độ phức tạp

Độ phức tạp tổng thể: **trung bình đến cao**.

| Phần | Độ khó | Lý do |
|------|--------|-------|
| Foundation (repo, Docker, DB) | Thấp | Quen thuộc, nhiều tài liệu. |
| Ingestion | Trung bình | Parser nhiều định dạng, chunking, embedding, trạng thái lỗi. |
| RAG pipeline + phân quyền retrieval | Cao | Lỗi cô lập dữ liệu là lỗi bảo mật, cần test kỹ. |
| Dataset đánh giá | Cao (tốn công) | Viết và duyệt tay khoảng 100 case có reference context chính xác. |
| Evaluation + metric sinh | Cao | Cần hiểu cách tính và thiên lệch của LLM-as-a-Judge. |
| Security Testing | Cao | Thiết kế test case có ý nghĩa và đánh giá kết quả không máy móc. |
| Benchmark, báo cáo | Trung bình | Phụ thuộc phần Evaluation đã ổn định. |

## 5. Rủi ro lớn nhất và cách giảm thiểu

| # | Rủi ro | Hậu quả | Cách giảm thiểu |
|---|--------|---------|-----------------|
| R1 | **Phạm vi phình to** (nhiều module, nhiều provider, nhiều tính năng giao diện) | Không bao giờ xong, bỏ dở giữa chừng | MVP chặt; làm tuần tự theo gate; thứ tự cắt khi trễ: giao diện nâng cao, xuất PDF, nhiều LLM provider, LlamaIndex. |
| R2 | **Dataset yếu hoặc sai** (ground truth, reference context không chính xác) | Mọi metric đều vô nghĩa dù code đúng | Duyệt tay từng case; đóng băng version đã duyệt; có câu hỏi không có đáp án trong tài liệu; ghi nguồn và quyền sử dụng tài liệu. |
| R3 | **LLM-as-a-Judge thiếu tin cậy** (thiên lệch, không ổn định giữa các lần chạy) | Điểm Faithfulness hay Relevancy gây hiểu lầm | Kết hợp metric xác định (Precision@K, Recall@K, MRR, NDCG@K) với judge và chấm tay một mẫu; ghi rõ judge model, prompt của judge và mức đồng thuận đo được. |
| R4 | **Rò rỉ dữ liệu giữa các user** do lọc quyền sai ở tầng retrieval | Lỗi bảo mật ngay trong sản phẩm làm về bảo mật | Lọc theo user ở tầng truy vấn vector, không chỉ ở API; test tự động có câu hỏi cố tình nhắm vào dữ liệu của user khác (gate M4). |
| R5 | **Không tái lập được kết quả** (LLM không xác định, nhà cung cấp đổi model, quên ghi cấu hình) | Không so sánh được hai lần chạy | Lưu đầy đủ metadata mỗi run; cố định dataset version; nêu rõ phần ngẫu nhiên không loại bỏ được. |
| R6 | **Chi phí và rate limit của LLM provider** | Chạy evaluation lớn bị chặn hoặc tốn tiền ngoài dự tính | Bắt đầu với ít provider; ghi token và chi phí ước tính từng run; có retry, timeout; thử trên tập nhỏ trước khi chạy cả dataset. |
| R7 | **Quá tải kiến thức** (RAG, metric, bảo mật AI, DB, DevOps cùng lúc) | Chậm, nản, hiểu nông | Lộ trình học gắn từng milestone (task M1-T10); học theo nhu cầu của task hiện tại; ưu tiên nền tảng, tránh gom thêm framework. |
| R8 | **Kiểm thử bảo mật vượt phạm vi hoặc tuyên bố quá mức** | Rủi ro đạo đức và mất uy tín | Chỉ test ứng dụng RAG do chính dự án kiểm soát, dùng dữ liệu giả và canary token; báo cáo nêu phần chưa kiểm tra; không dùng cụm "an toàn tuyệt đối". |

## 6. Điều chưa biết (cần quyết định ở các task sau)

- Tên model embedding cụ thể và số chiều vector: chốt sau một lần gọi thử provider, trước M3-T01 (provider đã chọn A1 ở `06_deployment_tech.md`).
- Nguồn tài liệu để xây corpus đánh giá và quyền sử dụng chúng (task M5-T03).
- Ngân sách chi phí chạy evaluation. Chưa có số liệu, sẽ có sau khi chạy baseline.
