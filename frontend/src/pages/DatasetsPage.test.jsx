import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api/datasetApi.js", () => ({
  listDatasets: vi.fn(),
  createDataset: vi.fn(),
  listVersions: vi.fn(),
  createVersion: vi.fn(),
  reviewVersion: vi.fn(),
  listTestCases: vi.fn(),
  addTestCase: vi.fn(),
  updateTestCase: vi.fn(),
  deleteTestCase: vi.fn(),
  importTestCases: vi.fn(),
}));
vi.mock("../services/api/documentApi.js", () => ({ listDocuments: vi.fn() }));

import * as api from "../services/api/datasetApi.js";
import { listDocuments } from "../services/api/documentApi.js";
import { ApiError } from "../services/api/httpClient.js";
import DatasetsPage from "./DatasetsPage.jsx";

const DRAFT = { id: "v1", dataset_id: "d1", version_number: 1, status: "draft", test_case_count: 1 };
const CASE = {
  id: "c1",
  question: "Hạn nộp hồ sơ?",
  ground_truth_answer: "30 ngày",
  question_type: "fact",
  difficulty: "easy",
  expected_behavior: "answer",
  source_note: null,
  reference_contexts: [{ filename: "quy-dinh.pdf", text: "trong vòng 30 ngày", char_start: 0, char_end: 18, document_content_hash: "h" }],
};

async function openDataset() {
  render(<DatasetsPage />);
  await userEvent.click(await screen.findByRole("button", { name: "Bộ quy định" }));
  await screen.findByText("Hạn nộp hồ sơ?");
}

describe("DatasetsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listDatasets.mockResolvedValue({ items: [{ id: "d1", name: "Bộ quy định" }], total: 1 });
    api.listVersions.mockResolvedValue({ items: [DRAFT] });
    api.listTestCases.mockResolvedValue({ items: [CASE], total: 1 });
    listDocuments.mockResolvedValue({ items: [{ id: "doc1", filename: "quy-dinh.pdf" }] });
  });

  it("tạo dataset mới rồi mở nó", async () => {
    api.createDataset.mockResolvedValue({ id: "d1", name: "Bộ quy định" });
    render(<DatasetsPage />);

    await userEvent.type(screen.getByLabelText("Tên dataset mới"), "Bộ mới");
    await userEvent.click(screen.getByRole("button", { name: "Tạo" }));

    await waitFor(() => expect(api.createDataset).toHaveBeenCalledWith("Bộ mới"));
    expect(await screen.findByText("Hạn nộp hồ sơ?")).toBeInTheDocument();
  });

  it("hiện câu hỏi với đáp án, loại, độ khó và đoạn trích nguồn", async () => {
    await openDataset();

    const row = screen.getByText("Hạn nộp hồ sơ?").closest("tr");
    expect(within(row).getByText("30 ngày")).toBeInTheDocument();
    expect(within(row).getByText("Sự kiện")).toBeInTheDocument();
    expect(within(row).getByText(/quy-dinh\.pdf: “trong vòng 30 ngày”/)).toBeInTheDocument();
  });

  it("thêm câu hỏi kèm tài liệu và câu trích", async () => {
    api.addTestCase.mockResolvedValue({ ...CASE, id: "c2" });
    await openDataset();

    await userEvent.click(screen.getByRole("button", { name: "Thêm câu hỏi" }));
    await userEvent.type(screen.getByLabelText("Câu hỏi"), "Phí năm đầu?");
    await userEvent.type(screen.getByLabelText("Đáp án chuẩn"), "Miễn phí");
    await userEvent.type(screen.getByLabelText("Câu trích 1"), "không phải đóng lệ phí");
    await userEvent.click(screen.getByRole("button", { name: "Thêm" }));

    await waitFor(() =>
      expect(api.addTestCase).toHaveBeenCalledWith("v1", {
        question: "Phí năm đầu?",
        ground_truth_answer: "Miễn phí",
        question_type: "fact",
        difficulty: "easy",
        expected_behavior: "answer",
        source_note: null,
        reference_contexts: [{ document_id: "doc1", quote: "không phải đóng lệ phí" }],
      }),
    );
  });

  it("câu không có đáp án gửi đúng hành vi mong đợi và không kèm câu trích", async () => {
    api.addTestCase.mockResolvedValue({ ...CASE, id: "c3" });
    await openDataset();

    await userEvent.click(screen.getByRole("button", { name: "Thêm câu hỏi" }));
    await userEvent.type(screen.getByLabelText("Câu hỏi"), "Lương giám đốc?");
    await userEvent.selectOptions(screen.getByLabelText("Loại câu hỏi"), "unanswerable");
    expect(screen.queryByLabelText("Đáp án chuẩn")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Thêm" }));

    await waitFor(() =>
      expect(api.addTestCase).toHaveBeenCalledWith("v1", expect.objectContaining({
        expected_behavior: "insufficient_context",
        ground_truth_answer: null,
        reference_contexts: [],
      })),
    );
  });

  it("lỗi kiểm chứng câu trích hiện ngay trong form", async () => {
    api.addTestCase.mockRejectedValue(new ApiError("quy-dinh.pdf: Không tìm thấy câu trích trong tài liệu", { status: 422 }));
    await openDataset();

    await userEvent.click(screen.getByRole("button", { name: "Thêm câu hỏi" }));
    await userEvent.type(screen.getByLabelText("Câu hỏi"), "x");
    await userEvent.type(screen.getByLabelText("Đáp án chuẩn"), "y");
    await userEvent.type(screen.getByLabelText("Câu trích 1"), "không có thật");
    await userEvent.click(screen.getByRole("button", { name: "Thêm" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Không tìm thấy câu trích");
  });

  it("import lỗi hiện danh sách lỗi theo dòng", async () => {
    api.importTestCases.mockRejectedValue(
      new ApiError("File import có lỗi; không test case nào được ghi", {
        status: 422,
        details: [{ row: 2, issue: "Thiếu câu hỏi" }, { row: 5, issue: "difficulty sai" }],
      }),
    );
    await openDataset();

    await userEvent.upload(screen.getByLabelText("Chọn file câu hỏi"), new File(["[]"], "cases.json", { type: "application/json" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("không test case nào được ghi");
    expect(alert).toHaveTextContent("Dòng 2: Thiếu câu hỏi");
    expect(alert).toHaveTextContent("Dòng 5: difficulty sai");
  });

  it("duyệt phiên bản sau khi xác nhận, rồi khóa việc sửa", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    api.reviewVersion.mockResolvedValue({ ...DRAFT, status: "reviewed" });
    await openDataset();
    api.listVersions.mockResolvedValue({ items: [{ ...DRAFT, status: "reviewed" }] });

    await userEvent.click(screen.getByRole("button", { name: "Duyệt và đóng băng" }));

    await waitFor(() => expect(api.reviewVersion).toHaveBeenCalledWith("v1"));
    expect(await screen.findByText(/Phiên bản đã duyệt: chỉ xem/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Thêm câu hỏi" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sửa" })).not.toBeInTheDocument();
  });

  it("tạo phiên bản mới sao chép từ phiên bản đang xem", async () => {
    api.createVersion.mockResolvedValue({ ...DRAFT, id: "v2", version_number: 2 });
    await openDataset();

    await userEvent.click(screen.getByRole("button", { name: "Tạo phiên bản mới từ bản này" }));

    await waitFor(() => expect(api.createVersion).toHaveBeenCalledWith("d1", "v1"));
  });

  it("lọc theo loại câu hỏi gọi API với bộ lọc", async () => {
    await openDataset();

    await userEvent.selectOptions(screen.getByLabelText("Lọc theo loại"), "unanswerable");

    await waitFor(() => expect(api.listTestCases).toHaveBeenLastCalledWith("v1", { questionType: "unanswerable", difficulty: "" }));
  });
});
