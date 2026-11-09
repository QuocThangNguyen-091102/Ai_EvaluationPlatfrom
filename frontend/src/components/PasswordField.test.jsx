import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import PasswordField from "./PasswordField.jsx";

function Field({ showStrength = false }) {
  const [value, setValue] = useState("");
  return <PasswordField label="Mật khẩu" value={value} onChange={setValue} autoComplete="new-password" showStrength={showStrength} />;
}

describe("PasswordField", () => {
  it("nút con mắt chuyển giữa hiện và ẩn mật khẩu", async () => {
    render(<Field />);
    const input = screen.getByLabelText("Mật khẩu");
    expect(input).toHaveAttribute("type", "password");

    await userEvent.click(screen.getByRole("button", { name: "Hiện mật khẩu" }));

    expect(input).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "Ẩn mật khẩu" })).toHaveAttribute("aria-pressed", "true");
  });

  it("độ mạnh tăng theo số điều kiện đạt; chỉ điều kiện độ dài ghi là bắt buộc", async () => {
    render(<Field showStrength />);

    expect(screen.getByText("Ít nhất 8 ký tự (bắt buộc)")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Mật khẩu"), "abc");
    expect(screen.getByText("Yếu")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Mật khẩu"), "defgh1A!");
    expect(screen.getByText("Mạnh")).toBeInTheDocument();
    expect(screen.getByText("Ít nhất 8 ký tự (bắt buộc)").closest("li")).toHaveClass("ok");
  });

  it("chế độ đăng nhập không hiện thanh độ mạnh", () => {
    render(<Field />);

    expect(screen.queryByText("Độ mạnh")).not.toBeInTheDocument();
  });
});
