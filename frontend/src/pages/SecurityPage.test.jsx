import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api/securityApi.js", () => ({
  listSecurityTestCases: vi.fn(),
  createSecurityRun: vi.fn(),
  listSecurityRuns: vi.fn(),
  listSecurityResults: vi.fn(),
  downloadSecurityReport: vi.fn(),
}));
vi.mock("../services/api/modelConfigApi.js", () => ({ listConfigurations: vi.fn(), getCapabilities: vi.fn() }));

import * as configApi from "../services/api/modelConfigApi.js";
import * as api from "../services/api/securityApi.js";
import SecurityPage from "./SecurityPage.jsx";

const RUN = {
  id: "s1",
  status: "completed",
  model_configuration_id: "m1",
  categories: [],
  total_cases: 3,
  completed_cases: 3,
  judge_model: null,
  judge_prompt_version: null,
  summary: { by_status: { pass: 1, fail: 1, skipped: 1 }, failed_by_severity: { critical: 1 } },
  coverage_notes: ["Không kết luận hệ thống an toàn tuyệt đối."],
  environment: { model_configuration: { llm_provider: "extractive", llm_model: "top-passages", prompt_version: "rag-grounded-citations", top_k: 5 } },
  error_message: null,
  started_at: "2026-11-06T08:00:00Z",
  finished_at: "2026-11-06T08:01:00Z",
  created_at: "2026-11-06T08:00:00Z",
};
const FAILED = {
  id: "r1",
  test_case_id: "t1",
  case_key: "DL-02",
  category: "data_leakage",
  title: "Đòi secret cấu hình",
  description: "mô tả",
  expected_behavior: "không lộ",
  status: "fail",
  severity: "critical",
  actual_response: "khóa là ...",
  evidence: { violations: [{ rule: "forbid_secrets", detail: "Lộ secret: JWT_SECRET" }] },
  evaluator: "rule",
  mitigation: "giữ secret trong biến môi trường",
  error_message: null,
  latency_ms: 10,
  contexts: [],
};

describe("SecurityPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listSecurityTestCases.mockResolvedValue({
      items: [
        { key: "AC-01", category: "access_control" },
        { key: "AC-02", category: "access_control" },
      ],
    });
    api.listSecurityRuns.mockResolvedValue({ items: [RUN], total: 1 });
    api.listSecurityResults.mockResolvedValue({ items: [FAILED], total: 1 });
    configApi.listConfigurations.mockResolvedValue({ items: [] });
    configApi.getCapabilities.mockResolvedValue({ llm_configured: false });
  });

  it("tạo lượt với các nhóm đã chọn", async () => {
    api.createSecurityRun.mockResolvedValue({ ...RUN, id: "s2", status: "pending" });
    render(<SecurityPage />);

    await userEvent.click(await screen.findByLabelText(/Kiểm soát truy cập/));
    expect(screen.getByText("(2)")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Chạy kiểm thử" }));

    await waitFor(() =>
      expect(api.createSecurityRun).toHaveBeenCalledWith({ modelConfigurationId: "", categories: ["access_control"], judgeModel: "" }),
    );
  });

  it("hiển thị tổng hợp, giới hạn và bằng chứng của test không đạt", async () => {
    render(<SecurityPage />);

    await userEvent.click(await screen.findByRole("button", { name: /top-passages/ }));

    expect(await screen.findByText("Lộ secret: JWT_SECRET")).toBeInTheDocument();
    expect(screen.getByText("Nghiêm trọng: 1", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Không kết luận hệ thống an toàn tuyệt đối.")).toBeInTheDocument();
    expect(screen.getByText("Không đạt", { selector: ".badge" })).toBeInTheDocument();
  });

  it("lọc theo mức độ", async () => {
    render(<SecurityPage />);
    await userEvent.click(await screen.findByRole("button", { name: /top-passages/ }));

    await userEvent.selectOptions(await screen.findByLabelText("Mức độ"), "critical");

    await waitFor(() => expect(api.listSecurityResults).toHaveBeenLastCalledWith("s1", { status: "", severity: "critical", category: "" }));
  });
});
