// Nhãn và giải thích metric đánh giá RAG, dùng chung cho trang Đánh giá và Dashboard.
// Không có ngưỡng "đạt/không đạt": chưa có baseline nên không tô màu tốt/xấu.

export const METRIC_LABELS = {
  behavior_correct: {
    label: "Hành vi đúng",
    hint: "Tỉ lệ câu hệ thống trả lời khi nên trả lời và từ chối khi tài liệu không có thông tin (so khớp quy tắc).",
  },
  precision_at_k: { label: "Precision@k", hint: "Trong k đoạn lấy về, bao nhiêu phần là đoạn đúng (chia cho k)." },
  recall_at_k: { label: "Recall@k", hint: "Bao nhiêu phần đoạn tham chiếu được tìm thấy trong k đoạn đầu." },
  mrr: { label: "MRR", hint: "Trung bình 1/(thứ hạng của đoạn đúng đầu tiên); 1 nghĩa là đoạn đúng luôn đứng đầu." },
  reciprocal_rank: { label: "Reciprocal rank", hint: "1/(thứ hạng của đoạn đúng đầu tiên)." },
  ndcg_at_k: { label: "NDCG@k", hint: "Chất lượng thứ tự: đoạn đúng càng đứng trên càng cao điểm." },
  faithfulness: {
    label: "Faithfulness",
    hint: "LLM judge: tỉ lệ ý trong câu trả lời được ngữ cảnh hỗ trợ. Judge có thể sai, nên đọc kèm câu trả lời.",
  },
  answer_relevancy: {
    label: "Answer relevancy",
    hint: "LLM judge: câu trả lời có đúng trọng tâm câu hỏi không (thang 1–5, quy về 0–1).",
  },
};

export const CATEGORY_LABELS = {
  ok: "Đạt",
  hallucination: "Bịa (trả lời khi nên từ chối)",
  false_refusal: "Từ chối sai",
  retrieval_miss: "Truy xuất trượt",
  unsupported_claims: "Ý không có căn cứ",
  error: "Lỗi hệ thống",
};

export const RUN_STATUS_LABELS = {
  pending: "Đang chờ",
  running: "Đang chạy",
  completed: "Hoàn tất",
  failed: "Lỗi",
};

export const METRIC_STATUS_LABELS = { skipped: "bỏ qua", failed: "không chấm được" };

export function metricName(metric) {
  const base = METRIC_LABELS[metric.metric_name]?.label ?? metric.metric_name;
  return metric.k ? base.replace("@k", `@${metric.k}`) : base;
}

export function formatScore(value) {
  if (value == null) return "—";
  return value.toFixed(3).replace(".", ",");
}
