import { describe, expect, it } from "vitest";

import { describeError, formatContentType, formatFileSize } from "./formatting.js";

describe("formatFileSize", () => {
  it.each([
    [0, "0 B"],
    [1023, "1023 B"],
    [1024, "1,0 KB"],
    [1536, "1,5 KB"],
    [1024 * 1024, "1,0 MB"],
    [5.5 * 1024 * 1024, "5,5 MB"],
  ])("%i byte -> %s", (bytes, expected) => {
    expect(formatFileSize(bytes)).toBe(expected);
  });
});

describe("formatContentType", () => {
  it("rút gọn các loại được hỗ trợ và giữ nguyên loại lạ", () => {
    expect(formatContentType("application/pdf")).toBe("PDF");
    expect(formatContentType("text/plain")).toBe("TXT");
    expect(formatContentType("image/png")).toBe("image/png");
  });
});

describe("describeError", () => {
  it("nối các lý do khi lỗi 422 có danh sách trường", () => {
    const error = { message: "Dữ liệu gửi lên không hợp lệ", details: [{ field: "password", issue: "Mật khẩu quá ngắn" }] };

    expect(describeError(error)).toBe("Dữ liệu gửi lên không hợp lệ: Mật khẩu quá ngắn");
  });

  it("dùng thông điệp thường khi không có chi tiết", () => {
    expect(describeError({ message: "Email đã được đăng ký", details: { x: 1 } })).toBe("Email đã được đăng ký");
  });

  it("có thông điệp mặc định khi không có gì", () => {
    expect(describeError(undefined)).toBe("Đã xảy ra lỗi");
  });
});
