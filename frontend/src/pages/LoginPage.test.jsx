import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthContext } from "../contexts/AuthContext.jsx";
import { ApiError } from "../services/api/httpClient.js";
import LoginPage from "./LoginPage.jsx";

function renderPage({ status = "anonymous", login = vi.fn(), register = vi.fn(), from } = {}) {
  render(
    <AuthContext.Provider value={{ status, user: null, login, register }}>
      <MemoryRouter initialEntries={[{ pathname: "/login", state: from ? { from } : undefined }]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/documents" element={<p>Trang tài liệu</p>} />
          <Route path="/khac" element={<p>Trang khác</p>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
  return { login, register };
}

// Nút gửi form (khác với tab "Đăng nhập" có cùng chữ): là nút có type=submit.
const submitButton = () => document.querySelector('button[type="submit"]');

async function fillCredentials() {
  await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
  await userEvent.type(screen.getByLabelText("Mật khẩu"), "mat-khau-dai");
}

describe("LoginPage", () => {
  it("nút gửi bị khóa cho đến khi nhập đủ email và mật khẩu", async () => {
    renderPage();
    expect(submitButton()).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    expect(submitButton()).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Mật khẩu"), "x");
    expect(submitButton()).toBeEnabled();
  });

  it("đăng nhập gọi login rồi chuyển tới trang tài liệu", async () => {
    const { login } = renderPage({ login: vi.fn().mockResolvedValue() });

    await fillCredentials();
    await userEvent.click(submitButton());

    await waitFor(() => expect(screen.getByText("Trang tài liệu")).toBeInTheDocument());
    expect(login).toHaveBeenCalledWith("a@example.com", "mat-khau-dai");
  });

  it("chuyển về trang người dùng định vào trước khi bị yêu cầu đăng nhập", async () => {
    renderPage({ login: vi.fn().mockResolvedValue(), from: "/khac" });

    await fillCredentials();
    await userEvent.click(submitButton());

    await waitFor(() => expect(screen.getByText("Trang khác")).toBeInTheDocument());
  });

  it("hiện lỗi từ máy chủ và giữ nguyên trang khi đăng nhập thất bại", async () => {
    renderPage({ login: vi.fn().mockRejectedValue(new ApiError("Email hoặc mật khẩu không đúng", { status: 401 })) });

    await fillCredentials();
    await userEvent.click(submitButton());

    expect(await screen.findByRole("alert")).toHaveTextContent("Email hoặc mật khẩu không đúng");
    expect(screen.queryByText("Trang tài liệu")).not.toBeInTheDocument();
  });

  it("chế độ đăng ký gọi register, không gọi login trực tiếp", async () => {
    const { login, register } = renderPage({ register: vi.fn().mockResolvedValue() });
    await userEvent.click(screen.getByRole("tab", { name: "Đăng ký" }));

    await fillCredentials();
    await userEvent.click(submitButton());

    await waitFor(() => expect(register).toHaveBeenCalledWith("a@example.com", "mat-khau-dai"));
    expect(login).not.toHaveBeenCalled();
  });

  it("hiện lý do cụ thể khi đăng ký bị từ chối vì dữ liệu không hợp lệ", async () => {
    const error = new ApiError("Dữ liệu gửi lên không hợp lệ", {
      status: 422,
      details: [{ field: "password", issue: "Mật khẩu phải có ít nhất 8 ký tự" }],
    });
    renderPage({ register: vi.fn().mockRejectedValue(error) });
    await userEvent.click(screen.getByRole("tab", { name: "Đăng ký" }));

    await fillCredentials();
    await userEvent.click(submitButton());

    expect(await screen.findByRole("alert")).toHaveTextContent("Mật khẩu phải có ít nhất 8 ký tự");
  });

  it("xóa lỗi cũ khi đổi giữa đăng nhập và đăng ký", async () => {
    renderPage({ login: vi.fn().mockRejectedValue(new ApiError("Sai thông tin", { status: 401 })) });
    await fillCredentials();
    await userEvent.click(submitButton());
    expect(await screen.findByRole("alert")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "Đăng ký" }));

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("đã đăng nhập thì chuyển đi luôn, không hiện form", () => {
    renderPage({ status: "authenticated" });

    expect(screen.getByText("Trang tài liệu")).toBeInTheDocument();
  });
});
