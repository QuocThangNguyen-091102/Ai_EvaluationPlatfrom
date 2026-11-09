import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import SpoilerText from "./SpoilerText.jsx";

describe("SpoilerText", () => {
  it("che nội dung sau một nút có nhãn; bấm thì hiện, Che lại thì che tiếp", async () => {
    render(<SpoilerText label="Bấm để hiện câu trả lời">CNRY-3451-ZQ</SpoilerText>);

    const cover = screen.getByRole("button", { name: "Bấm để hiện câu trả lời" });
    expect(screen.queryByRole("button", { name: "Che lại" })).not.toBeInTheDocument();

    await userEvent.click(cover);

    expect(screen.queryByRole("button", { name: "Bấm để hiện câu trả lời" })).not.toBeInTheDocument();
    expect(screen.getByText("CNRY-3451-ZQ")).toHaveClass("is-open");

    await userEvent.click(screen.getByRole("button", { name: "Che lại" }));

    expect(screen.getByRole("button", { name: "Bấm để hiện câu trả lời" })).toBeInTheDocument();
  });

  it("mở được bằng bàn phím", async () => {
    render(<SpoilerText>nội dung</SpoilerText>);

    await userEvent.tab();
    await userEvent.keyboard("{Enter}");

    expect(screen.getByText("nội dung")).toHaveClass("is-open");
  });
});
