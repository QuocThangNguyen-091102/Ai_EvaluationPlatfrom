// Định dạng hiển thị bằng tiếng Việt.

export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1).replace(".", ",")} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
}

export function formatDateTime(isoString) {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" }).format(new Date(isoString));
}

const TYPE_LABELS = {
  "application/pdf": "PDF",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
  "text/plain": "TXT",
};

export function formatContentType(contentType) {
  return TYPE_LABELS[contentType] ?? contentType;
}

export function formatLatency(milliseconds) {
  if (milliseconds == null) return "độ trễ: không rõ";
  if (milliseconds < 1000) return `${milliseconds} ms`;
  return `${(milliseconds / 1000).toFixed(1).replace(".", ",")} s`;
}

// Chi phí null nghĩa là không biết giá (không phải miễn phí), nên hiển thị "không rõ" thay vì 0.
export function formatCost(cost) {
  if (cost == null) return "không rõ";
  const value = Number(cost);
  if (value === 0) return "0";
  return `$${value.toFixed(6).replace(/0+$/, "").replace(/\.$/, "")}`;
}

export const STATUS_LABELS = {
  uploaded: "Đã tải lên",
  processing: "Đang xử lý",
  ready: "Sẵn sàng",
  failed: "Lỗi",
};

// Chuyển lỗi từ API thành thông điệp hiển thị; lỗi 422 kèm danh sách trường thì nối các lý do lại.
export function describeError(error) {
  if (Array.isArray(error?.details) && error.details.length > 0) {
    const reasons = error.details.map((item) => item.issue).filter(Boolean);
    if (reasons.length > 0) return `${error.message}: ${reasons.join("; ")}`;
  }
  return error?.message ?? "Đã xảy ra lỗi";
}
