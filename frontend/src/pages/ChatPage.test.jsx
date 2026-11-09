import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api/chatApi.js", () => ({
  askQuestion: vi.fn(),
  listSessions: vi.fn(),
  getSessionMessages: vi.fn(),
  deleteSession: vi.fn(),
}));
vi.mock("../services/api/modelConfigApi.js", () => ({
  getCapabilities: vi.fn(),
  listConfigurations: vi.fn(),
}));

import * as chatApi from "../services/api/chatApi.js";
import { ApiError } from "../services/api/httpClient.js";
import * as modelConfigApi from "../services/api/modelConfigApi.js";
import ChatPage from "./ChatPage.jsx";

const SOURCE = { number: 1, chunk_id: "c1", filename: "quy-dinh.pdf", page_number: 3, score: 0.91, snippet: "Hồ sơ nộp trong 30 ngày." };

function answer(overrides = {}) {
  return {
    session_id: "s1",
    message_id: "m1",
    answer: "Phải nộp trong 30 ngày [1].",
    insufficient_context: false,
    mode: "llm",
    citations: [SOURCE],
    sources: [SOURCE],
    metrics: { latency_ms: 1250, prompt_tokens: 120, completion_tokens: 30, estimated_cost: null },
    model_configuration_id: "cfg",
    ...overrides,
  };
}

async function ask(text) {
  await userEvent.type(screen.getByLabelText("Câu hỏi"), text);
  await userEvent.click(screen.getByRole("button", { name: "Gửi" }));
}

describe("ChatPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    chatApi.listSessions.mockResolvedValue({ items: [], total: 0 });
    modelConfigApi.listConfigurations.mockResolvedValue({ items: [] });
    modelConfigApi.getCapabilities.mockResolvedValue({ llm_configured: true, prompt_versions: ["rag-grounded-citations"] });
  });

  it("gửi câu hỏi rồi hiện câu trả lời, nguồn trích dẫn và số đo", async () => {
    chatApi.askQuestion.mockResolvedValue(answer());
    render(<ChatPage />);

    await ask("Hạn nộp hồ sơ?");

    expect(await screen.findByText(/Phải nộp trong 30 ngày/)).toBeInTheDocument();
    expect(chatApi.askQuestion).toHaveBeenCalledWith({ question: "Hạn nộp hồ sơ?", sessionId: null, modelConfigurationId: undefined });
    // Số [1] trong câu trả lời thành nút dẫn tới nguồn; thẻ nguồn được trích dẫn hiện tên file.
    expect(screen.getByRole("button", { name: "Nguồn 1: quy-dinh.pdf, trang 3" })).toBeInTheDocument();
    expect(screen.getByText("quy-dinh.pdf", { selector: ".cited-answer__card b" })).toBeInTheDocument();
    expect(screen.getByText(/1,3 s · 120 \+ 30 token · chi phí ước tính: không rõ/)).toBeInTheDocument();
    expect(screen.getByText("LLM")).toBeInTheDocument();
  });

  it("câu hỏi tiếp theo đi vào cùng cuộc hội thoại", async () => {
    chatApi.askQuestion.mockResolvedValueOnce(answer()).mockResolvedValueOnce(answer({ message_id: "m2", answer: "Không thu phí." }));
    render(<ChatPage />);

    await ask("Câu một");
    await screen.findByText(/Phải nộp trong 30 ngày/);
    await ask("Câu hai");

    await waitFor(() => expect(chatApi.askQuestion).toHaveBeenLastCalledWith({ question: "Câu hai", sessionId: "s1", modelConfigurationId: undefined }));
  });

  it("đánh dấu rõ câu trả lời không dùng LLM và câu không đủ thông tin", async () => {
    modelConfigApi.getCapabilities.mockResolvedValue({ llm_configured: false, prompt_versions: ["rag-grounded-citations"] });
    chatApi.askQuestion.mockResolvedValue(
      answer({ mode: "extractive", answer: "Hệ thống chưa cấu hình LLM...", metrics: { latency_ms: 80, prompt_tokens: null, completion_tokens: null, estimated_cost: "0" } }),
    );
    render(<ChatPage />);

    expect(await screen.findByRole("note")).toHaveTextContent("chưa cấu hình LLM");
    await ask("x");
    expect(await screen.findByText("Không dùng LLM")).toBeInTheDocument();
    expect(screen.getByText(/chi phí ước tính: 0$/)).toBeInTheDocument();
  });

  it("câu trả lời từ chối được gắn nhãn không đủ thông tin", async () => {
    chatApi.askQuestion.mockResolvedValue(
      answer({ answer: "Không đủ thông tin trong tài liệu để trả lời câu hỏi này.", insufficient_context: true, citations: [], sources: [] }),
    );
    render(<ChatPage />);

    await ask("Lương giám đốc?");

    expect(await screen.findByText("Không đủ thông tin")).toBeInTheDocument();
  });

  it("lỗi của máy chủ hiện ngay trong cuộc hội thoại", async () => {
    chatApi.askQuestion.mockRejectedValue(new ApiError("Không kết nối được tới LLM", { status: 502 }));
    render(<ChatPage />);

    await ask("x");

    expect(await screen.findByRole("alert")).toHaveTextContent("Không kết nối được tới LLM");
  });

  it("chọn cấu hình thì câu hỏi gửi kèm id cấu hình", async () => {
    modelConfigApi.listConfigurations.mockResolvedValue({ items: [{ id: "cfg-2", name: "Top-K 10" }] });
    chatApi.askQuestion.mockResolvedValue(answer());
    render(<ChatPage />);
    await screen.findByRole("option", { name: "Top-K 10" });

    await userEvent.selectOptions(screen.getByLabelText("Cấu hình"), "cfg-2");
    await ask("x");

    await waitFor(() => expect(chatApi.askQuestion).toHaveBeenCalledWith({ question: "x", sessionId: null, modelConfigurationId: "cfg-2" }));
  });

  it("mở cuộc hội thoại cũ thì tải lịch sử kèm nguồn", async () => {
    chatApi.listSessions.mockResolvedValue({ items: [{ id: "s9", title: "Hồ sơ nộp khi nào?" }], total: 1 });
    chatApi.getSessionMessages.mockResolvedValue({
      items: [
        { id: "u", role: "user", content: "Hồ sơ nộp khi nào?", citations: [], sources: [], metrics: {}, insufficient_context: false, error_message: null },
        { id: "a", role: "assistant", content: "Trong 30 ngày [1].", citations: [SOURCE], sources: [SOURCE], metrics: { latency_ms: 900, prompt_tokens: 10, completion_tokens: 5, estimated_cost: null }, insufficient_context: false, error_message: null },
      ],
    });
    render(<ChatPage />);

    await userEvent.click(await screen.findByRole("button", { name: "Hồ sơ nộp khi nào?" }));

    expect(await screen.findByText(/Trong 30 ngày/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nguồn 1: quy-dinh.pdf, trang 3" })).toBeInTheDocument();
    expect(chatApi.getSessionMessages).toHaveBeenCalledWith("s9");
    expect(screen.getByText("Các đoạn đã tham khảo (1)")).toBeInTheDocument();
  });

  it("xóa cuộc hội thoại sau khi xác nhận", async () => {
    chatApi.listSessions.mockResolvedValue({ items: [{ id: "s9", title: "Cũ" }], total: 1 });
    chatApi.deleteSession.mockResolvedValue(null);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<ChatPage />);

    await userEvent.click(await screen.findByRole("button", { name: "Xóa cuộc hội thoại Cũ" }));

    await waitFor(() => expect(chatApi.deleteSession).toHaveBeenCalledWith("s9"));
  });

  it("không gửi câu hỏi rỗng", async () => {
    render(<ChatPage />);
    await screen.findByText(/Đặt câu hỏi/);

    expect(screen.getByRole("button", { name: "Gửi" })).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Câu hỏi"), "   ");
    expect(screen.getByRole("button", { name: "Gửi" })).toBeDisabled();
  });

  it("Enter để gửi, Shift+Enter để xuống dòng", async () => {
    chatApi.askQuestion.mockResolvedValue(answer());
    render(<ChatPage />);
    const box = screen.getByLabelText("Câu hỏi");

    await userEvent.type(box, "dòng một{Shift>}{Enter}{/Shift}dòng hai");
    expect(chatApi.askQuestion).not.toHaveBeenCalled();
    await userEvent.type(box, "{Enter}");

    await waitFor(() => expect(chatApi.askQuestion).toHaveBeenCalledWith(expect.objectContaining({ question: "dòng một\ndòng hai" })));
    const messages = await screen.findAllByRole("article");
    expect(within(messages[0]).getByText(/dòng một/)).toBeInTheDocument();
  });
});
