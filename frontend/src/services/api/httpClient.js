// Lớp gọi API duy nhất của frontend. Các file *Api.js dùng hàm này, không gọi fetch trực tiếp.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Lỗi chuẩn hóa theo định dạng lỗi trong docs/08_api_contracts.md.
export class ApiError extends Error {
  constructor(message, { status, code, details } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let authToken = null;
let onUnauthorized = () => {};

export function setAuthToken(token) {
  authToken = token;
}

// Hàm này được gọi khi server trả 401 cho một request đã gửi kèm token (token hết hạn hoặc không còn hiệu lực).
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler ?? (() => {});
}

// `responseType: "blob"` dùng cho tải file (báo cáo CSV); lỗi vẫn đọc dạng JSON như mọi request khác.
export async function request(path, { method = "GET", json, formData, auth = true, responseType = "json" } = {}) {
  const headers = {};
  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (formData !== undefined) {
    body = formData; // trình duyệt tự đặt Content-Type kèm ranh giới multipart
  }
  const sentToken = auth ? authToken : null;
  if (sentToken) {
    headers.Authorization = `Bearer ${sentToken}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { method, headers, body });
  } catch {
    throw new ApiError("Không kết nối được tới máy chủ", { status: 0, code: "network_error" });
  }

  if (response.status === 204) {
    return null;
  }
  if (response.ok && responseType === "blob") {
    return response.blob();
  }
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401 && sentToken) {
      onUnauthorized();
    }
    const error = payload?.error;
    // /health trả trực tiếp {status, database}, không bọc trong "error".
    const message = error?.message ?? (payload?.status ? `Máy chủ báo trạng thái: ${payload.status}` : "Yêu cầu thất bại");
    throw new ApiError(message, { status: response.status, code: error?.code, details: error?.details ?? payload });
  }
  return payload;
}
