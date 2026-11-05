import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api/authApi.js", () => ({
  login: vi.fn(),
  register: vi.fn(),
  getCurrentUser: vi.fn(),
}));

import { useAuth } from "../hooks/useAuth.js";
import * as authApi from "../services/api/authApi.js";
import { request, setAuthToken } from "../services/api/httpClient.js";
import { AuthProvider } from "./AuthContext.jsx";

const TOKEN_KEY = "ai-eval.token";
const USER = { id: "1", email: "a@example.com", created_at: "2026-01-01T00:00:00Z" };

function Probe() {
  const { status, user, login, register, logout } = useAuth();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="email">{user?.email ?? "-"}</span>
      <button onClick={() => login("a@example.com", "pw").catch(() => {})}>login</button>
      <button onClick={() => register("a@example.com", "pw").catch(() => {})}>register</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

function renderProbe() {
  return render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
}

const status = () => screen.getByTestId("status");

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setAuthToken(null);
  });

  it("là anonymous khi chưa có token đã lưu", async () => {
    renderProbe();

    await waitFor(() => expect(status()).toHaveTextContent("anonymous"));
    expect(authApi.getCurrentUser).not.toHaveBeenCalled();
  });

  it("khôi phục phiên khi token đã lưu còn hợp lệ", async () => {
    window.localStorage.setItem(TOKEN_KEY, "token-cu");
    authApi.getCurrentUser.mockResolvedValue(USER);

    renderProbe();

    await waitFor(() => expect(status()).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("email")).toHaveTextContent("a@example.com");
  });

  it("xóa token đã lưu khi token không còn hợp lệ", async () => {
    window.localStorage.setItem(TOKEN_KEY, "token-het-han");
    authApi.getCurrentUser.mockRejectedValue(new Error("401"));

    renderProbe();

    await waitFor(() => expect(status()).toHaveTextContent("anonymous"));
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("đăng nhập lưu token và đặt user", async () => {
    authApi.login.mockResolvedValue({ access_token: "token-moi" });
    authApi.getCurrentUser.mockResolvedValue(USER);
    renderProbe();
    await waitFor(() => expect(status()).toHaveTextContent("anonymous"));

    await userEvent.click(screen.getByText("login"));

    await waitFor(() => expect(status()).toHaveTextContent("authenticated"));
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("token-moi");
  });

  it("không lưu token nếu lấy thông tin user thất bại sau khi đăng nhập", async () => {
    authApi.login.mockResolvedValue({ access_token: "token-moi" });
    authApi.getCurrentUser.mockRejectedValue(new Error("me lỗi"));
    renderProbe();
    await waitFor(() => expect(status()).toHaveTextContent("anonymous"));

    await userEvent.click(screen.getByText("login"));

    await waitFor(() => expect(authApi.getCurrentUser).toHaveBeenCalled());
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(status()).toHaveTextContent("anonymous");
  });

  it("đăng ký rồi tự đăng nhập", async () => {
    authApi.register.mockResolvedValue(USER);
    authApi.login.mockResolvedValue({ access_token: "token-moi" });
    authApi.getCurrentUser.mockResolvedValue(USER);
    renderProbe();
    await waitFor(() => expect(status()).toHaveTextContent("anonymous"));

    await userEvent.click(screen.getByText("register"));

    await waitFor(() => expect(status()).toHaveTextContent("authenticated"));
    expect(authApi.register).toHaveBeenCalledWith("a@example.com", "pw");
    expect(authApi.login).toHaveBeenCalledWith("a@example.com", "pw");
  });

  it("đăng xuất xóa token và phiên", async () => {
    window.localStorage.setItem(TOKEN_KEY, "token-cu");
    authApi.getCurrentUser.mockResolvedValue(USER);
    renderProbe();
    await waitFor(() => expect(status()).toHaveTextContent("authenticated"));

    await userEvent.click(screen.getByText("logout"));

    expect(status()).toHaveTextContent("anonymous");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("tự đăng xuất khi một request có token bị server trả 401", async () => {
    window.localStorage.setItem(TOKEN_KEY, "token-cu");
    authApi.getCurrentUser.mockResolvedValue(USER);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ status: 401, ok: false, json: () => Promise.resolve({ error: { message: "hết hạn" } }) }),
    );
    renderProbe();
    await waitFor(() => expect(status()).toHaveTextContent("authenticated"));

    await request("/api/v1/documents").catch(() => {});

    await waitFor(() => expect(status()).toHaveTextContent("anonymous"));
    vi.unstubAllGlobals();
  });
});
