# Ghi chú metric đánh giá RAG (M6)

Tài liệu này giải thích từng metric được tính thế nào, khi nào không tính, và giới hạn của chúng. Đọc trước khi dùng số liệu để kết luận.

## 1. Nguyên tắc chung

- Mọi lượt đánh giá chạy qua **cùng RAG pipeline** với trang Hỏi đáp (`ai_engine/pipeline/rag_pipeline.py`). Không có pipeline riêng "cho đẹp số".
- Chỉ đánh giá được **phiên bản dataset đã duyệt** (bất biến), để chạy lại cho cùng bộ câu hỏi.
- Mỗi lượt lưu ảnh chụp môi trường (`environment`): cấu hình mô hình, phiên bản dataset, judge, phiên bản thư viện, cấu hình chunk thực tế của tài liệu, cảnh báo.
- Metric không tính được thì **không điền số**: trạng thái `skipped` (không áp dụng hoặc không chọn judge) hoặc `failed` (judge trả lời sai định dạng hoặc lỗi). DB có ràng buộc `status='computed'` ⇔ `value IS NOT NULL`.
- **Chưa có baseline**, nên giao diện không tô màu đạt/không đạt và không đặt ngưỡng.

## 2. Xác định "đoạn đúng" (relevance)

Người viết dataset dán câu trích nguyên văn; hệ thống lưu vị trí ký tự `(document_content_hash, char_start, char_end)` trong văn bản đã làm sạch. Một chunk lấy về là **đúng** nếu cùng tài liệu (cùng hash nội dung) và khoảng ký tự **giao nhau** với một tham chiếu.

Hệ quả cần biết:
- Không phụ thuộc cách chia chunk: đổi chunk size vẫn so được với cùng dataset.
- Giao nhau một ký tự cũng tính là đúng: chunk lớn dễ "đúng" hơn. Precision có thể bị thổi phồng khi chunk to.
- Câu không có đáp án (`insufficient_context`) không có tham chiếu, nên **không có metric truy xuất** (n trong dashboard nhỏ hơn tổng số câu là vì vậy).

## 3. Metric truy xuất (tất định)

| Metric | Cách tính | Ghi chú |
|---|---|---|
| Precision@k | số chunk đúng trong top k **chia cho k** | Chia cho k (không chia cho số chunk lấy về), nên lấy ít hơn k chunk sẽ bị phạt. Chỉ có 1 tham chiếu thì tối đa ≈ 1/k: Precision@5 = 0,2 không có nghĩa là truy xuất kém. |
| Recall@k | số tham chiếu được ít nhất một chunk trong top k phủ / tổng tham chiếu | Đếm theo tham chiếu, không theo chunk. |
| Reciprocal rank / MRR | 1 / thứ hạng chunk đúng đầu tiên; 0 nếu không có | MRR là trung bình trên các câu có tham chiếu. |
| NDCG@k | gain = 1 cho chunk phủ thêm tham chiếu **mới**, chiết khấu log2(rank+1), chia cho NDCG lý tưởng | Chunk trùng lặp phủ lại cùng tham chiếu không được cộng điểm. |

## 4. Hành vi (tất định)

`behavior_correct` = 1 nếu hệ thống trả lời khi kỳ vọng trả lời, và từ chối (`insufficient_context`) khi kỳ vọng từ chối.

**Giới hạn của chế độ extractive** (không có LLM): chế độ này luôn trả các đoạn tốt nhất và chỉ "từ chối" khi không lấy được chunk nào. Vì vậy câu không có đáp án gần như luôn bị xếp loại `hallucination`. Đây là giới hạn của chế độ, không phải lỗi metric. E2E ngày 2026-11-06 với dataset MẪU: 2/2 câu không có đáp án bị xếp loại này.

## 5. Metric sinh câu trả lời (LLM judge)

Chỉ tính khi: câu kỳ vọng trả lời, hệ thống không từ chối, và câu trả lời do LLM viết (`mode="llm"`). Extractive không có gì để judge chấm.

| Metric | Cách tính |
|---|---|
| Faithfulness | Judge tách câu trả lời thành các ý, đánh dấu ý nào được ngữ cảnh hỗ trợ. Điểm = số ý được hỗ trợ / số ý. Không có ý nào thì `failed` (không gán 1). |
| Answer relevancy | Judge chấm 1–5 mức đúng trọng tâm; quy về (điểm − 1) / 4. |

Judge trả JSON sai định dạng thì metric là `failed` kèm lý do, không đoán số. Prompt judge có phiên bản (`judge-strict-json`, lưu trong mỗi lượt).

**Giới hạn và thiên lệch của LLM judge** (cần nhớ khi đọc số):
- Judge là một LLM, có thể sai. Phải đọc mẫu câu trả lời, không chỉ nhìn trung bình.
- Thiên vị câu trả lời dài, trôi chảy, và câu trả lời do cùng họ mô hình viết (self-preference). Nên dùng judge khác mô hình được chấm.
- Kết quả phụ thuộc phiên bản prompt judge và model judge: chỉ so sánh các lượt cùng judge và cùng `judge_prompt_version`.
- Chưa đo độ đồng thuận judge–người. Trước khi tin faithfulness, cần cho người chấm một mẫu khoảng 20–30 câu và so sánh.

## 5b. Context Precision và Context Recall (kiểu RAGAS)

| Metric | Cách tính | Cần LLM |
|---|---|---|
| Context Precision | Average precision trên các hạng có đoạn đúng: Σ(precision@k × rel_k) / số đoạn đúng. Đoạn đúng xác định tất định như mục 2 | Không |
| Context Recall | Judge tách **đáp án tham chiếu** thành các khẳng định và phán định từng khẳng định có được các đoạn lấy về hỗ trợ không; điểm = số được hỗ trợ / tổng. Dùng lại prompt faithfulness `judge-strict-json` | Có (judge), nhưng **không** cần câu trả lời của LLM nên chạy được cả ở chế độ trích đoạn |

Khác biệt với bản RAGAS gốc: Context Precision ở đây dùng nhãn đúng/sai tất định (theo câu trích tham chiếu) thay vì để LLM phán định từng đoạn, nên rẻ và lặp lại được nhưng phụ thuộc chất lượng câu trích. Context Precision chỉ đo **thứ tự**: lấy ít đoạn không bị phạt, thiếu tham chiếu cũng không bị phạt (xem Recall@k và Context Recall). Không lấy được đoạn nào thì Context Recall = 0 mà không cần gọi judge.

## 6. Phân loại lỗi mỗi câu

Thứ tự ưu tiên (lấy nhãn đầu tiên khớp): `error` (lỗi hệ thống) → `hallucination` (trả lời khi nên từ chối) → `false_refusal` (từ chối khi nên trả lời) → `retrieval_miss` (recall@k = 0) → `unsupported_claims` (faithfulness < 1) → `ok`.

Một câu chỉ có một nhãn, nên có thể che lỗi thứ hai (ví dụ vừa truy xuất trượt vừa bịa ý). Phân tích lỗi chi tiết: `docs/error_analysis.md`.

## 7. Tổng hợp

- Trung bình chỉ trên các giá trị `computed`. Chi tiết có `cases` (số câu có giá trị) và `statuses` (đếm computed, skipped, failed).
- Không có giá trị nào thì vẫn có dòng tổng hợp với `value = null`, trạng thái `skipped` hoặc `failed`, để giao diện ghi rõ thay vì ẩn đi.
- Bộ dataset nhỏ (ví dụ 6 câu) thì trung bình dao động rất mạnh. Chưa tính khoảng tin cậy; với dataset khoảng 100 câu nên bổ sung bootstrap trước khi so sánh hai cấu hình.

## 8. Câu lỗi và gián đoạn

- Một câu lỗi (provider sập, timeout) được ghi `status=error` kèm thông điệp; lượt vẫn chạy tiếp và vẫn `completed`. Xem `failed_cases`.
- Máy chủ khởi động lại khi lượt đang chạy: lượt bị đánh dấu `failed` (phục hồi lúc khởi động). Không tự chạy lại để tránh tốn chi phí LLM ngoài ý muốn.
