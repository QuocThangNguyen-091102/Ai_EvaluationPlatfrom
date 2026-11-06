import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api/benchmarkApi.js", () => ({
  createBenchmark: vi.fn(),
  listBenchmarks: vi.fn(),
  getBenchmark: vi.fn(),
  downloadBenchmarkReport: vi.fn(),
}));
vi.mock("../services/api/datasetApi.js", () => ({ listDatasets: vi.fn(), listVersions: vi.fn() }));
vi.mock("../services/api/modelConfigApi.js", () => ({
  listConfigurations: vi.fn(),
  getCapabilities: vi.fn(),
  createConfiguration: vi.fn(),
}));

import * as api from "../services/api/benchmarkApi.js";
import * as datasetApi from "../services/api/datasetApi.js";
import * as configApi from "../services/api/modelConfigApi.js";
import BenchmarksPage from "./BenchmarksPage.jsx";

const BASE_CONFIG = {
  id: "base",
  name: "Mặc định",
  llm_provider: "extractive",
  llm_model: "top-passages",
  prompt_version: "rag-v1",
  top_k: 5,
  temperature: 0,
  chunk_size: 250,
  chunk_overlap: 50,
};
const variant = (value, recall, p50) => ({
  evaluation_run_id: `r${value}`,
  model_configuration: { ...BASE_CONFIG, top_k: value },
  varied_value: value,
  status: "completed",
  total_cases: 6,
  completed_cases: 6,
  failed_cases: 0,
  categories: {},
  aggregate_metrics: [{ metric_name: "recall_at_k", k: value, value: recall, method: "deterministic", status: "computed", details: {} }],
  usage: { latency_mean_ms: p50, latency_p50_ms: p50, latency_p95_ms: p50, prompt_tokens: null, completion_tokens: null, total_cost: "0", cost_incomplete: false },
  error_message: null,
});
const BENCHMARK = {
  id: "b1",
  name: "So sánh top_k",
  dataset_version_id: "v1",
  varied_variable: "top_k",
  status: "completed",
  judge_model: null,
  notes: ["Các cấu hình còn khác nhau ở: temperature."],
  error_message: null,
  started_at: null,
  finished_at: null,
  created_at: "2026-11-06T08:00:00Z",
  variants: [variant(3, 0.5, 40), variant(5, 1, 55)],
};

describe("BenchmarksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listBenchmarks.mockResolvedValue({ items: [BENCHMARK], total: 1 });
    datasetApi.listDatasets.mockResolvedValue({ items: [{ id: "d1", name: "Bộ quy định" }] });
    datasetApi.listVersions.mockResolvedValue({ items: [{ id: "v1", version_number: 1, status: "reviewed", test_case_count: 6 }] });
    configApi.listConfigurations.mockResolvedValue({ items: [BASE_CONFIG] });
    configApi.getCapabilities.mockResolvedValue({ llm_configured: false });
  });

  it("tạo một cấu hình cho mỗi giá trị, chỉ đổi biến đã chọn, rồi tạo benchmark", async () => {
    configApi.createConfiguration.mockImplementation(async (body) => ({ id: `c${body.top_k}` }));
    api.createBenchmark.mockResolvedValue({ ...BENCHMARK, id: "b2", status: "pending" });
    render(<BenchmarksPage />);

    await userEvent.type(screen.getByLabelText("Tên benchmark"), "K");
    await userEvent.selectOptions(await screen.findByLabelText("Phiên bản dataset (đã duyệt)"), "v1");
    await userEvent.selectOptions(screen.getByLabelText("Cấu hình gốc"), "base");
    await userEvent.type(screen.getByLabelText("Các giá trị"), "3, 8, 3");
    await userEvent.click(screen.getByRole("button", { name: "Chạy benchmark" }));

    await waitFor(() => expect(api.createBenchmark).toHaveBeenCalled());
    expect(configApi.createConfiguration).toHaveBeenCalledTimes(2);
    expect(configApi.createConfiguration).toHaveBeenCalledWith(expect.objectContaining({ top_k: 8, temperature: 0, llm_model: "top-passages" }));
    expect(api.createBenchmark).toHaveBeenCalledWith(
      expect.objectContaining({ variedVariable: "top_k", modelConfigurationIds: ["c3", "c8"], datasetVersionId: "v1" }),
    );
  });

  it("cần ít nhất hai giá trị", async () => {
    render(<BenchmarksPage />);
    await userEvent.type(screen.getByLabelText("Tên benchmark"), "K");
    await userEvent.selectOptions(await screen.findByLabelText("Phiên bản dataset (đã duyệt)"), "v1");
    await userEvent.selectOptions(screen.getByLabelText("Cấu hình gốc"), "base");
    await userEvent.type(screen.getByLabelText("Các giá trị"), "5");

    await userEvent.click(screen.getByRole("button", { name: "Chạy benchmark" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("ít nhất 2 giá trị");
    expect(configApi.createConfiguration).not.toHaveBeenCalled();
  });

  it("hiển thị bảng so sánh và ghi chú điều kiện", async () => {
    render(<BenchmarksPage />);

    await userEvent.click(await screen.findByRole("button", { name: /So sánh top_k/ }));

    expect(screen.getByText("Các cấu hình còn khác nhau ở: temperature.")).toBeInTheDocument();
    expect(screen.getByText("0,500")).toBeInTheDocument();
    expect(screen.getByText("1,000")).toBeInTheDocument();
    expect(screen.getAllByText("55 ms").length).toBeGreaterThan(0);
  });
});
