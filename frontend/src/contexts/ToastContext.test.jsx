import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { useToast } from "../hooks/useToast.js";
import { ToastProvider } from "./ToastContext.jsx";

function Trigger({ message }) {
  const { notify } = useToast();
  return (
    <button type="button" onClick={() => notify(message)}>
      Gửi
    </button>
  );
}

describe("ToastProvider", () => {
  it("hiện toast với tiêu đề và chi tiết; lỗi dùng role alert", async () => {
    render(
      <ToastProvider>
        <Trigger message={{ tone: "error", title: "Lượt đánh giá bị lỗi", detail: "Hết thời gian chờ LLM" }} />
      </ToastProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: "Gửi" }));

    const toast = screen.getByRole("alert");
    expect(toast).toHaveTextContent("Lượt đánh giá bị lỗi");
    expect(toast).toHaveTextContent("Hết thời gian chờ LLM");
  });

  it("nút đóng gỡ toast khỏi màn hình", async () => {
    render(
      <ToastProvider>
        <Trigger message={{ tone: "success", title: "Đã xử lý xong tài liệu" }} />
      </ToastProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: "Gửi" }));
    await userEvent.click(screen.getByRole("button", { name: "Đóng thông báo" }));

    await waitFor(() => expect(screen.queryByText("Đã xử lý xong tài liệu")).not.toBeInTheDocument());
  });

  it("ngoài ToastProvider thì notify không làm gì và không ném lỗi", async () => {
    render(<Trigger message={{ title: "Không ai nghe" }} />);

    await userEvent.click(screen.getByRole("button", { name: "Gửi" }));

    expect(screen.queryByText("Không ai nghe")).not.toBeInTheDocument();
  });
});
