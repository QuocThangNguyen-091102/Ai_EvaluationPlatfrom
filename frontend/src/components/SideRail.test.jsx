import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import SideRail from "./SideRail.jsx";

function renderAt(path, onLogout = () => {}) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <SideRail email="ban@example.com" onLogout={onLogout} />
    </MemoryRouter>,
  );
}

describe("SideRail", () => {
  it("có đủ 7 trang và đánh dấu trang đang mở", () => {
    renderAt("/evaluations");

    const nav = screen.getByRole("navigation", { name: "Điều hướng chính" });
    expect(nav.querySelectorAll("a")).toHaveLength(7);
    expect(screen.getByRole("link", { name: "Đánh giá" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Tài liệu" })).not.toHaveAttribute("aria-current");
  });

  it("nút thu gọn hoặc mở rộng đổi trạng thái và nhớ lựa chọn", async () => {
    renderAt("/documents");

    const toggle = screen.getByRole("button", { name: "Mở rộng menu" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);

    expect(screen.getByRole("button", { name: "Thu gọn menu" })).toHaveAttribute("aria-expanded", "true");
    expect(window.localStorage.getItem("ai-eval.rail-wide")).toBe("1");
  });

  it("phím mũi tên chuyển focus giữa các mục", async () => {
    renderAt("/documents");

    screen.getByRole("link", { name: "Tài liệu" }).focus();
    await userEvent.keyboard("{ArrowDown}");

    expect(screen.getByRole("link", { name: "Hỏi đáp" })).toHaveFocus();
  });

  it("nút Đăng xuất gọi onLogout", async () => {
    const onLogout = vi.fn();
    renderAt("/documents", onLogout);

    await userEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));

    expect(onLogout).toHaveBeenCalledOnce();
  });
});
