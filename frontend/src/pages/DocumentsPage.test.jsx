import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api/documentApi.js", () => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
}));

import { ApiError } from "../services/api/httpClient.js";
import * as documentApi from "../services/api/documentApi.js";
import DocumentsPage from "./DocumentsPage.jsx";

function makeDocument(overrides = {}) {
  return {
    id: "doc-1",
    filename: "bao-cao.pdf",
    content_type: "application/pdf",
    size_bytes: 2048,
    status: "ready",
    error_message: null,
    chunk_count: 12,
    processing_config: null,
    created_at: "2026-11-05T10:00:00Z",
    updated_at: "2026-11-05T10:00:00Z",
    ...overrides,
  };
}

const listOf = (items, total = items.length) => ({ items, total, limit: 10, offset: 0 });

describe("DocumentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    documentApi.listDocuments.mockResolvedValue(listOf([]));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("hiện trạng thái trống khi chưa có tài liệu", async () => {
    render(<DocumentsPage />);

    expect(await screen.findByText(/Chưa có tài liệu nào/)).toBeInTheDocument();
  });

  it("hiện danh sách với loại, dung lượng, trạng thái và số đoạn", async () => {
    documentApi.listDocuments.mockResolvedValue(
      listOf([
        makeDocument(),
        makeDocument({ id: "doc-2", filename: "ghi-chu.txt", content_type: "text/plain", status: "processing", chunk_count: 0 }),
      ]),
    );

    render(<DocumentsPage />);

    const rows = await screen.findAllByRole("row");
    const first = within(rows[1]);
    expect(first.getByText("bao-cao.pdf")).toBeInTheDocument();
    expect(first.getByText("PDF")).toBeInTheDocument();
    expect(first.getByText("2,0 KB")).toBeInTheDocument();
    expect(first.getByText("Sẵn sàng")).toBeInTheDocument();
    expect(first.getByText("12")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Đang xử lý")).toBeInTheDocument();
  });

  it("hiện lý do khi tài liệu xử lý lỗi", async () => {
    documentApi.listDocuments.mockResolvedValue(
      listOf([makeDocument({ status: "failed", error_message: "Không đọc được file PDF (file có thể bị hỏng)" })]),
    );

    render(<DocumentsPage />);

    expect(await screen.findByText("Lỗi")).toBeInTheDocument();
    expect(screen.getByText(/Không đọc được file PDF/)).toBeInTheDocument();
  });

  it("hiện lỗi khi không tải được danh sách", async () => {
    documentApi.listDocuments.mockRejectedValue(new ApiError("Không kết nối được tới máy chủ", { status: 0 }));

    render(<DocumentsPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Không kết nối được tới máy chủ");
  });

  it("tải file lên rồi làm mới danh sách và báo kết quả", async () => {
    documentApi.uploadDocument.mockResolvedValue(makeDocument());
    render(<DocumentsPage />);
    await screen.findByText(/Chưa có tài liệu nào/);
    const file = new File(["nội dung"], "moi.txt", { type: "text/plain" });

    await userEvent.upload(screen.getByLabelText("Chọn file tài liệu"), file);

    await waitFor(() => expect(documentApi.uploadDocument).toHaveBeenCalledWith(file));
    const results = await screen.findByRole("list", { name: "Kết quả tải lên" });
    expect(within(results).getByText("moi.txt")).toBeInTheDocument();
    expect(within(results).getByText(/Đã tải lên/)).toBeInTheDocument();
    expect(documentApi.listDocuments.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("từ chối ngay trên giao diện file không đúng đuôi, không gọi API", async () => {
    render(<DocumentsPage />);
    await screen.findByText(/Chưa có tài liệu nào/);
    const file = new File(["MZ"], "virus.exe", { type: "application/octet-stream" });

    // applyAccept: false vì trình duyệt thật vẫn cho kéo thả file ngoài danh sách.
    await userEvent.upload(screen.getByLabelText("Chọn file tài liệu"), file, { applyAccept: false });

    expect(await screen.findByText(/Chỉ chấp nhận file PDF, DOCX hoặc TXT/)).toBeInTheDocument();
    expect(documentApi.uploadDocument).not.toHaveBeenCalled();
  });

  it("hiện lỗi của máy chủ cho từng file và vẫn tiếp tục các file còn lại", async () => {
    documentApi.uploadDocument
      .mockRejectedValueOnce(new ApiError("Bạn đã upload tài liệu có cùng nội dung", { status: 409 }))
      .mockResolvedValueOnce(makeDocument());
    render(<DocumentsPage />);
    await screen.findByText(/Chưa có tài liệu nào/);

    await userEvent.upload(screen.getByLabelText("Chọn file tài liệu"), [
      new File(["a"], "trung.txt", { type: "text/plain" }),
      new File(["b"], "moi.txt", { type: "text/plain" }),
    ]);

    const results = await screen.findByRole("list", { name: "Kết quả tải lên" });
    expect(within(results).getByText(/cùng nội dung/)).toBeInTheDocument();
    expect(within(results).getByText(/moi\.txt/)).toBeInTheDocument();
    expect(documentApi.uploadDocument).toHaveBeenCalledTimes(2);
  });

  it("xóa tài liệu sau khi người dùng xác nhận", async () => {
    documentApi.listDocuments.mockResolvedValue(listOf([makeDocument()]));
    documentApi.deleteDocument.mockResolvedValue(null);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<DocumentsPage />);

    await userEvent.click(await screen.findByRole("button", { name: "Xóa" }));

    await waitFor(() => expect(documentApi.deleteDocument).toHaveBeenCalledWith("doc-1"));
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("bao-cao.pdf"));
  });

  it("không xóa khi người dùng hủy xác nhận", async () => {
    documentApi.listDocuments.mockResolvedValue(listOf([makeDocument()]));
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<DocumentsPage />);

    await userEvent.click(await screen.findByRole("button", { name: "Xóa" }));

    expect(documentApi.deleteDocument).not.toHaveBeenCalled();
  });

  it("hiện lỗi khi xóa thất bại", async () => {
    documentApi.listDocuments.mockResolvedValue(listOf([makeDocument()]));
    documentApi.deleteDocument.mockRejectedValue(new ApiError("Không tìm thấy tài liệu", { status: 404 }));
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<DocumentsPage />);

    await userEvent.click(await screen.findByRole("button", { name: "Xóa" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Không tìm thấy tài liệu");
  });

  it("phân trang: chuyển sang trang sau gọi API với offset mới", async () => {
    documentApi.listDocuments.mockResolvedValue({ items: [makeDocument()], total: 25, limit: 10, offset: 0 });
    render(<DocumentsPage />);
    expect(await screen.findByText("Trang 1 / 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Trước" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Sau" }));

    await waitFor(() => expect(documentApi.listDocuments).toHaveBeenLastCalledWith({ limit: 10, offset: 10 }));
    expect(await screen.findByText("Trang 2 / 3")).toBeInTheDocument();
  });

  it("không hiện phân trang khi chỉ có một trang", async () => {
    documentApi.listDocuments.mockResolvedValue(listOf([makeDocument()]));
    render(<DocumentsPage />);
    await screen.findByText("bao-cao.pdf");

    expect(screen.queryByRole("navigation", { name: "Phân trang" })).not.toBeInTheDocument();
  });

  it("tự làm mới khi còn tài liệu đang xử lý và dừng khi tất cả đã xong", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    documentApi.listDocuments
      .mockResolvedValueOnce(listOf([makeDocument({ status: "processing", chunk_count: 0 })]))
      .mockResolvedValue(listOf([makeDocument({ status: "ready" })]));
    render(<DocumentsPage />);
    expect(await screen.findByText("Đang xử lý")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3100);
    });

    expect(await screen.findByText("Sẵn sàng")).toBeInTheDocument();
    const callsAfterReady = documentApi.listDocuments.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });
    expect(documentApi.listDocuments.mock.calls.length).toBe(callsAfterReady);
  });
});
