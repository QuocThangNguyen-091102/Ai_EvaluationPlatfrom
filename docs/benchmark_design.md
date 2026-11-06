# Thiết kế benchmark (M8)

## 1. Mục tiêu

So sánh nhiều cấu hình RAG một cách **công bằng**: cùng phiên bản dataset đã duyệt, cùng corpus, cùng code chấm điểm, và mỗi lần chỉ thay **một biến**: `llm_model`, `top_k` hoặc `prompt_version`.

## 2. Cách làm

- Benchmark **không có logic chấm riêng**. Mỗi cấu hình là một `EvaluationRun` bình thường (`evaluation_runs.benchmark_run_id` trỏ về benchmark), chạy qua cùng `EvaluationRunner` và cùng RAG pipeline. Nhờ vậy số liệu ở trang Benchmark luôn khớp với trang Đánh giá.
- Các lượt con chạy **tuần tự** trong nền. Máy chủ miễn phí chỉ có ít RAM, không nên chạy song song nhiều lượt cùng giữ model embedding.
- Tạo benchmark là **một transaction**: kiểm tra version đã duyệt và mọi cấu hình trước, rồi mới ghi. Lỗi ở cấu hình nào cũng không để lại benchmark hay lượt con dở dang.
- Kiểm tra điều kiện so sánh (`evaluation/benchmarks/benchmark_runner.py::config_differences`):
  - Các cấu hình phải có giá trị **khác nhau từng đôi một** ở biến đã khai báo; nếu không thì trả lỗi 422.
  - Nếu còn khác ở biến khác (temperature, chunk, embedding, ...), benchmark vẫn chạy nhưng ghi **cảnh báo** vào `notes`, vì khác biệt kết quả không thể quy hết cho biến đã khai báo.
- Giao diện tạo các cấu hình bằng cách chép cấu hình gốc và chỉ đổi đúng biến được chọn, nên điều kiện "một biến" được đảm bảo ngay từ đầu.

## 3. Chỉ số so sánh

| Nhóm | Chỉ số | Ghi chú |
|---|---|---|
| Chất lượng | Trung bình metric của từng lượt (xem `docs/metrics_notes.md`) | Chỉ so được trên cùng dataset version |
| Độ trễ | Trung bình, p50, p95 trên các câu chạy được | Percentile theo nearest-rank (luôn là một giá trị đo thật). Bộ câu hỏi nhỏ thì p95 gần bằng giá trị lớn nhất |
| Token | Tổng token vào và ra | `null` khi provider không báo số token (không đoán) |
| Chi phí | Tổng chi phí ước tính theo `configs/models.yaml` | Câu không có giá thì **không cộng như 0**: `cost_incomplete = true`, giao diện ghi "thiếu giá một phần" |

## 4. Đọc kết quả đúng cách

Ví dụ từ E2E ngày 2026-11-06 (dataset MẪU 6 câu, chế độ trích đoạn; chỉ để kiểm tra luồng, **không phải kết quả chất lượng**):

| top_k | Recall@k | Precision@k | NDCG@k |
|---|---|---|---|
| 1 | 1,000 | 1,000 | 1,000 |
| 3 | 1,000 | 0,333 | 0,807 |
| 5 | 1,000 | 0,200 | 0,807 |

Precision giảm khi tăng k vì mỗi câu chỉ có một đoạn tham chiếu và Precision@k chia cho k; truy xuất không hề kém đi. Muốn chọn top_k, cần nhìn Recall, chất lượng câu trả lời (faithfulness khi có LLM), token và chi phí, không nhìn riêng Precision.

## 5. Giới hạn

- Chưa có kiểm định thống kê hay khoảng tin cậy. Khác biệt nhỏ trên bộ câu hỏi nhỏ có thể chỉ do ngẫu nhiên (đặc biệt với LLM có temperature > 0).
- Độ trễ phụ thuộc máy chủ và tải lúc chạy; chỉ so sánh trong cùng một benchmark.
- Đổi `chunk_size` không phải biến của benchmark: chunk là thuộc tính của tài liệu đã xử lý, muốn so phải xử lý lại corpus.
- Bảng `reports` (lịch sử xuất báo cáo) chưa làm. Báo cáo CSV được dựng lại từ DB mỗi lần tải, nên luôn khớp dữ liệu.
