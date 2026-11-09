import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api/evaluationApi.js", () => ({
  createEvaluation: vi.fn(),
  listEvaluations: vi.fn(),
  getEvaluation: vi.fn(),
  listResults: vi.fn(),
  downloadReport: vi.fn(),
}));
vi.mock("../services/api/datasetApi.js", () => ({ listDatasets: vi.fn(), listVersions: vi.fn() }));
vi.mock("../services/api/modelConfigApi.js", () => ({ listConfigurations: vi.fn(), getCapabilities: vi.fn() }));
vi.mock("../services/api/documentApi.js", () => ({ listDocuments: vi.fn(() => Promise.resolve({ items: [], total: 3 })) }));
vi.mock("../services/api/chatApi.js", () => ({ listSessions: vi.fn(() => Promise.resolve({ items: [], total: 0 })) }));
vi.mock("../services/api/securityApi.js", () => ({
  listSecurityRuns: vi.fn(() => Promise.resolve({ items: [], total: 0 })),
}));
vi.mock("../services/api/benchmarkApi.js", () => ({ listBenchmarks: vi.fn(() => Promise.resolve({ items: [], total: 0 })) }));

import * as datasetApi from "../services/api/datasetApi.js";
import * as api from "../services/api/evaluationApi.js";
import { ApiError } from "../services/api/httpClient.js";
import * as configApi from "../services/api/modelConfigApi.js";
import DashboardPage from "./DashboardPage.jsx";
import EvaluationsPage from "./EvaluationsPage.jsx";

const ENVIRONMENT = {
  dataset_version: { id: "v1", version_number: 2, cases: 2 },
  model_configuration: { llm_provider: "extractive", llm_model: "top-passages", top_k: 5, prompt_version: "rag-grounded-citations", chunk_size: 250, chunk_overlap: 50 },
  warnings: [],
};
const RUN = {
  id: "r1",
  status: "completed",
  dataset_version_id: "v1",
  model_configuration_id: "m1",
  judge_model: null,
  judge_prompt_version: null,
  total_cases: 2,
  completed_cases: 2,
  failed_cases: 0,
  categories: { ok: 1, hallucination: 1 },
  aggregate_metrics: [
    { metric_name: "recall_at_k", k: 5, value: 0.75, method: "deterministic", status: "computed", details: { cases: 1 } },
    { metric_name: "faithfulness", k: null, value: null, method: "llm_judge", status: "skipped", details: { cases: 0 } },
  ],
  environment: ENVIRONMENT,
  error_message: null,
  started_at: "2026-11-06T08:00:00Z",
  finished_at: "2026-11-06T08:01:00Z",
  created_at: "2026-11-06T08:00:00Z",
};
const RESULT = {
  id: "res1",
  test_case_id: "c1",
  question: "Hạn nộp hồ sơ?",
  expected_behavior: "answer",
  ground_truth_answer: "30 ngày",
  status: "ok",
  category: "ok",
  answer: "Trong vòng 30 ngày [1]",
  insufficient_context: false,
  mode: "extractive",
  error_message: null,
  latency_ms: 120,
  prompt_tokens: null,
  completion_tokens: null,
  estimated_cost: "0",
  metrics: [{ metric_name: "recall_at_k", k: 5, value: 1, method: "deterministic", status: "computed", details: {} }],
  contexts: [{ rank: 1, filename: "quy-dinh.pdf", page_number: 1, score: 0.91, snippet: "trong vòng 30 ngày", relevant: true }],
};

function renderPage(page) {
  return render(<MemoryRouter>{page}</MemoryRouter>);
}

describe("EvaluationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listEvaluations.mockResolvedValue({ items: [RUN], total: 1 });
    api.getEvaluation.mockResolvedValue(RUN);
    api.listResults.mockResolvedValue({ items: [RESULT], total: 1 });
    datasetApi.listDatasets.mockResolvedValue({ items: [{ id: "d1", name: "Bộ quy định" }] });
    datasetApi.listVersions.mockResolvedValue({
      items: [
        { id: "v1", version_number: 2, status: "reviewed", test_case_count: 2 },
        { id: "v0", version_number: 1, status: "draft", test_case_count: 2 },
      ],
    });
    configApi.listConfigurations.mockResolvedValue({ items: [] });
    configApi.getCapabilities.mockResolvedValue({ llm_configured: false });
  });

  it("chỉ cho chọn phiên bản đã duyệt và tạo lượt đánh giá", async () => {
    api.createEvaluation.mockResolvedValue({ ...RUN, status: "pending" });
    renderPage(<EvaluationsPage />);

    const select = await screen.findByLabelText("Phiên bản dataset (đã duyệt)");
    await screen.findByRole("option", { name: /phiên bản 2/ });
    expect(screen.queryByRole("option", { name: /phiên bản 1 / })).not.toBeInTheDocument();
    expect(screen.getByText(/chưa cấu hình LLM/)).toBeInTheDocument();

    await userEvent.selectOptions(select, "v1");
    await userEvent.click(screen.getByRole("button", { name: "Chạy đánh giá" }));

    await waitFor(() => expect(api.createEvaluation).toHaveBeenCalledWith({ datasetVersionId: "v1", modelConfigurationId: "", judgeModel: "" }));
  });

  it("hiển thị metric tổng hợp, metric bị bỏ qua và kết quả từng câu", async () => {
    renderPage(<EvaluationsPage />);

    await userEvent.click(await screen.findByRole("button", { name: /top-passages/ }));

    expect(await screen.findByText("Recall@5")).toBeInTheDocument();
    expect(screen.getByText("0,750")).toBeInTheDocument();
    expect(screen.getByText("bỏ qua")).toBeInTheDocument();
    expect(await screen.findByText("Hạn nộp hồ sơ?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Bịa/ })).toBeInTheDocument();
  });

  it("bấm một câu mở panel chi tiết; Esc đóng và trả focus về dòng đó", async () => {
    renderPage(<EvaluationsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /top-passages/ }));

    const row = await screen.findByRole("button", { name: "Câu 1: Hạn nộp hồ sơ?" });
    await userEvent.click(row);

    const panel = screen.getByRole("dialog", { name: "Chi tiết câu hỏi" });
    expect(panel).toHaveTextContent("Câu trả lời của hệ thống");
    expect(panel).toHaveTextContent("Đoạn lấy về");

    await userEvent.keyboard("{Escape}");

    expect(screen.queryByRole("dialog", { name: "Chi tiết câu hỏi" })).not.toBeInTheDocument();
    expect(row).toHaveFocus();
  });

  it("lọc kết quả theo phân loại lỗi", async () => {
    renderPage(<EvaluationsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /top-passages/ }));

    await userEvent.click(await screen.findByRole("button", { name: /Bịa/ }));

    await waitFor(() => expect(api.listResults).toHaveBeenLastCalledWith("r1", { status: "", category: "hallucination" }));
  });

  it("báo lỗi khi API từ chối tạo lượt", async () => {
    api.createEvaluation.mockRejectedValue(new ApiError("Chỉ đánh giá được phiên bản dataset đã duyệt", { status: 409 }));
    renderPage(<EvaluationsPage />);
    await userEvent.selectOptions(await screen.findByLabelText("Phiên bản dataset (đã duyệt)"), "v1");

    await userEvent.click(screen.getByRole("button", { name: "Chạy đánh giá" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("đã duyệt");
  });
});

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("so sánh các lượt hoàn tất theo phiên bản dataset", async () => {
    api.listEvaluations.mockResolvedValue({ items: [RUN, { ...RUN, id: "r2", dataset_version_id: "v9" }], total: 2 });
    renderPage(<DashboardPage />);

    expect(await screen.findAllByRole("table")).toHaveLength(2);
    expect(api.listEvaluations).toHaveBeenCalledWith({ status: "completed", limit: 100 });
    expect(screen.getAllByText("0,750")).toHaveLength(2);
    expect(screen.getAllByText("Bịa (trả lời khi nên từ chối) (1)")).toHaveLength(2);
  });

  it("tổng quan đếm dữ liệu của từng khu vực", async () => {
    api.listEvaluations.mockResolvedValue({ items: [], total: 0 });
    datasetApi.listDatasets.mockResolvedValue({ items: [{ id: "d1" }], total: 1 });
    renderPage(<DashboardPage />);

    const documents = await screen.findByRole("link", { name: /Tài liệu/ });
    await waitFor(() => expect(documents).toHaveTextContent("3"));
    expect(screen.getByRole("link", { name: /Benchmark/ })).toHaveAttribute("href", "/benchmarks");
  });

  it("hướng dẫn tạo lượt khi chưa có dữ liệu", async () => {
    api.listEvaluations.mockResolvedValue({ items: [], total: 0 });
    renderPage(<DashboardPage />);

    expect(await screen.findByRole("link", { name: "Tạo lượt đánh giá" })).toHaveAttribute("href", "/evaluations");
  });
});
