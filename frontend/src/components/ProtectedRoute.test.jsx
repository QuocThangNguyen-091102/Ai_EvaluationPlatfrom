import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthContext } from "../contexts/AuthContext.jsx";
import ProtectedRoute from "./ProtectedRoute.jsx";

function renderAt(status) {
  return render(
    <AuthContext.Provider value={{ status, user: null }}>
      <MemoryRouter initialEntries={["/documents"]}>
        <Routes>
          <Route path="/login" element={<p>Trang đăng nhập</p>} />
          <Route
            path="/documents"
            element={
              <ProtectedRoute>
                <p>Nội dung riêng tư</p>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe("ProtectedRoute", () => {
  it("chuyển về trang đăng nhập khi chưa đăng nhập và không lộ nội dung", () => {
    renderAt("anonymous");

    expect(screen.getByText("Trang đăng nhập")).toBeInTheDocument();
    expect(screen.queryByText("Nội dung riêng tư")).not.toBeInTheDocument();
  });

  it("hiện thông báo chờ khi đang kiểm tra phiên, chưa chuyển trang vội", () => {
    renderAt("loading");

    expect(screen.getByText(/Đang kiểm tra phiên đăng nhập/)).toBeInTheDocument();
    expect(screen.queryByText("Trang đăng nhập")).not.toBeInTheDocument();
  });

  it("hiện nội dung khi đã đăng nhập", () => {
    renderAt("authenticated");

    expect(screen.getByText("Nội dung riêng tư")).toBeInTheDocument();
  });
});
