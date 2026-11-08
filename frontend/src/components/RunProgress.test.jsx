import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RunProgress from "./RunProgress.jsx";

const TIMES = {
  createdAt: "2026-11-08T03:00:00Z",
  startedAt: "2026-11-08T03:00:05Z",
  finishedAt: "2026-11-08T03:02:10Z",
};

function props(overrides) {
  return { status: "running", completed: 3, total: 10, unit: "câu", ...TIMES, ...overrides };
}

describe("RunProgress", () => {
  it("khi đang chờ: thanh không xác định tiến độ, chỉ có mốc vào hàng đợi", () => {
    render(<RunProgress {...props({ status: "pending", completed: 0, startedAt: null, finishedAt: null })} />);

    const bar = screen.getByRole("progressbar");
    expect(bar).not.toHaveAttribute("aria-valuenow");
    expect(bar).toHaveAttribute("aria-valuetext", "Đang chờ");
    expect(screen.getByRole("status")).toHaveTextContent("Đang chờ");
    expect(screen.getByText("Đang chờ tới lượt chạy")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  it("khi đang chạy: thanh xác định tiến độ theo số mục đã xong", () => {
    render(<RunProgress {...props({ finishedAt: null })} />);

    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "3");
    expect(bar).toHaveAttribute("aria-valuemax", "10");
    expect(screen.getByText("30%")).toBeInTheDocument();
    expect(screen.getByText("Đang chạy 3/10 câu")).toBeInTheDocument();
  });

  it("ghi số mục lỗi khi có", () => {
    render(<RunProgress {...props({ finishedAt: null, failed: 2 })} />);

    expect(screen.getByText("3/10 câu · 2 lỗi")).toBeInTheDocument();
  });

  it("lượt chạy đã xong từ trước thì không hiện gì", () => {
    const { container } = render(<RunProgress {...props({ status: "completed", completed: 10 })} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("lượt chạy kết thúc trong lúc đang xem thì giữ trạng thái Hoàn tất và thời lượng thật", () => {
    const { rerender } = render(<RunProgress {...props({ finishedAt: null })} />);
    rerender(<RunProgress {...props({ status: "completed", completed: 10 })} />);

    expect(screen.getByRole("status")).toHaveTextContent("Hoàn tất");
    expect(screen.getByText("Đã chạy xong 10 câu")).toBeInTheDocument();
    expect(screen.getByText("2 phút 5 giây")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("lượt chạy lỗi trong lúc đang xem thì hiện điểm dừng", () => {
    const { rerender } = render(<RunProgress {...props({ finishedAt: null })} />);
    rerender(<RunProgress {...props({ status: "failed", completed: 4 })} />);

    expect(screen.getByRole("status")).toHaveTextContent("Lỗi");
    expect(screen.getAllByText("Dừng ở 4/10 câu")).toHaveLength(2);
  });
});
