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

export async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch {
    throw new ApiError("Không kết nối được tới backend", { status: 0, code: "network_error" });
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const error = body?.error;
    // /health trả trực tiếp {status, database}, không bọc trong "error".
    const message = error?.message ?? (body?.status ? `Backend báo trạng thái: ${body.status}` : "Yêu cầu thất bại");
    throw new ApiError(message, { status: response.status, code: error?.code, details: error?.details ?? body });
  }
  return body;
}
