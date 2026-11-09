import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import CitedAnswer from "./CitedAnswer.jsx";

const SOURCES = [
  { number: 1, chunk_id: "c1", filename: "sao-hoa.txt", page_number: null, score: 0.9, snippet: "Sao Hỏa có hai vệ tinh tự nhiên." },
  { number: 2, chunk_id: "c2", filename: "sao-moc.txt", page_number: 4, score: 0.8, snippet: "Sao Mộc là hành tinh lớn nhất." },
];

function renderAnswer(text, citations = SOURCES) {
  return render(<CitedAnswer text={text} sources={SOURCES} citations={citations} />);
}

describe("CitedAnswer", () => {
  it("biến mỗi số nguồn thành nút có tên rõ ràng và giữ nguyên số không khớp nguồn nào", () => {
    renderAnswer("Sao Hỏa có hai vệ tinh [1]. Sao Mộc lớn nhất [1][2]. Ý lạ [7].");

    expect(screen.getAllByRole("button", { name: "Nguồn 1: sao-hoa.txt, không rõ trang" })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Nguồn 2: sao-moc.txt, trang 4" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Nguồn 7/ })).not.toBeInTheDocument();
    expect(screen.getByText(/\[7\]/)).toBeInTheDocument();
  });

  it("focus vào số nguồn thì gạch chân đúng ý đó và hiện đoạn trích của nguồn", async () => {
    renderAnswer("Sao Hỏa có hai vệ tinh [1]. Sao Mộc lớn nhất [2].");

    await userEvent.tab();

    expect(screen.getByText("Sao Hỏa có hai vệ tinh")).toHaveClass("is-hl");
    // Dấu ". " sau [1] thuộc ý trước: ý sau bắt đầu đúng bằng chữ, không gạch chân dấu câu.
    expect(screen.getByText("Sao Mộc lớn nhất")).not.toHaveClass("is-hl");
    expect(screen.getByRole("tooltip", { hidden: true })).toHaveTextContent("Sao Hỏa có hai vệ tinh tự nhiên.");
  });

  it("focus vào thẻ nguồn thì đánh dấu mọi ý dùng nguồn đó", async () => {
    renderAnswer("Ý một [2]. Ý hai [1]. Ý ba [2].");

    act(() => screen.getByLabelText(/^Nguồn 2: sao-moc\.txt, trang 4\. Đánh dấu/).focus());

    expect(screen.getByText("Ý một")).toHaveClass("is-hl");
    expect(screen.getByText(/Ý hai/)).not.toHaveClass("is-hl");
    expect(screen.getByText(/Ý ba/)).toHaveClass("is-hl");
  });

  it("câu trả lời không có số nguồn hiển thị như văn bản thường", () => {
    renderAnswer("Không đủ thông tin trong tài liệu.", []);

    expect(screen.getByText("Không đủ thông tin trong tài liệu.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
