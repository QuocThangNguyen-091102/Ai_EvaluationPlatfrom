import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, request, setAuthToken, setUnauthorizedHandler } from "./httpClient.js";

function respond(status, body) {
  return Promise.resolve({
    status,
    ok: status >= 200 && status < 300,
    json: () => (body === undefined ? Promise.reject(new Error("no body")) : Promise.resolve(body)),
  });
}

describe("httpClient.request", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    setAuthToken(null);
    setUnauthorizedHandler(null);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("gửi token trong header Authorization khi đã có token", async () => {
    setAuthToken("abc");
    fetch.mockReturnValue(respond(200, {}));

    await request("/x");

    expect(fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer abc");
  });

  it("không gửi token khi auth=false", async () => {
    setAuthToken("abc");
    fetch.mockReturnValue(respond(200, {}));

    await request("/x", { auth: false });

    expect(fetch.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it("gửi JSON kèm Content-Type", async () => {
    fetch.mockReturnValue(respond(200, {}));

    await request("/x", { method: "POST", json: { a: 1 } });

    const init = fetch.mock.calls[0][1];
    expect(init.method).toBe("POST");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe('{"a":1}');
  });

  it("gửi FormData mà không tự đặt Content-Type (để trình duyệt thêm ranh giới multipart)", async () => {
    fetch.mockReturnValue(respond(200, {}));
    const formData = new FormData();

    await request("/x", { method: "POST", formData });

    const init = fetch.mock.calls[0][1];
    expect(init.body).toBe(formData);
    expect(init.headers["Content-Type"]).toBeUndefined();
  });

  it("trả null với phản hồi 204", async () => {
    fetch.mockReturnValue(respond(204));

    expect(await request("/x", { method: "DELETE" })).toBeNull();
  });

  it("chuyển lỗi của API thành ApiError có mã, thông điệp và chi tiết", async () => {
    fetch.mockReturnValue(
      respond(409, { error: { code: "conflict", message: "Email đã được đăng ký", details: { field: "email" } } }),
    );

    const error = await request("/x").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, code: "conflict", message: "Email đã được đăng ký", details: { field: "email" } });
  });

  it("báo lỗi mạng bằng thông điệp tiếng Việt", async () => {
    fetch.mockRejectedValue(new TypeError("Failed to fetch"));

    const error = await request("/x").catch((e) => e);

    expect(error).toMatchObject({ status: 0, code: "network_error", message: "Không kết nối được tới máy chủ" });
  });

  it("gọi handler khi server trả 401 cho request đã gửi token", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    setAuthToken("het-han");
    fetch.mockReturnValue(respond(401, { error: { code: "unauthorized", message: "hết hạn", details: null } }));

    await request("/x").catch(() => {});

    expect(handler).toHaveBeenCalledOnce();
  });

  it("không gọi handler khi 401 đến từ request không có token (ví dụ đăng nhập sai)", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    fetch.mockReturnValue(respond(401, { error: { code: "unauthorized", message: "sai mật khẩu", details: null } }));

    await request("/x", { auth: false }).catch(() => {});

    expect(handler).not.toHaveBeenCalled();
  });

  it("đọc được phản hồi lỗi kiểu /health (không bọc trong error)", async () => {
    fetch.mockReturnValue(respond(503, { status: "degraded", database: "error" }));

    const error = await request("/health").catch((e) => e);

    expect(error.message).toContain("degraded");
  });
});
