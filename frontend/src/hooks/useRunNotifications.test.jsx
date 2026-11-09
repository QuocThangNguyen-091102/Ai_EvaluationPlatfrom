import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ToastContext } from "../contexts/ToastContext.jsx";
import { useRunNotifications } from "./useRunNotifications.js";

const isUnfinished = (status) => status === "pending" || status === "running";
const describeRun = (run) => ({ tone: run.status === "completed" ? "success" : "error", title: `${run.id} ${run.status}` });

function Probe({ runs }) {
  useRunNotifications(runs, { isUnfinished, describe: describeRun });
  return <p>đang theo dõi</p>;
}

function renderWith(notify, runs) {
  const view = render(
    <ToastContext.Provider value={{ notify }}>
      <Probe runs={runs} />
    </ToastContext.Provider>,
  );
  return (nextRuns) =>
    view.rerender(
      <ToastContext.Provider value={{ notify }}>
        <Probe runs={nextRuns} />
      </ToastContext.Provider>,
    );
}

describe("useRunNotifications", () => {
  it("không thông báo những lượt đã xong từ trước khi mở trang", () => {
    const notify = vi.fn();
    renderWith(notify, [{ id: "a", status: "completed" }]);

    expect(screen.getByText("đang theo dõi")).toBeInTheDocument();
    expect(notify).not.toHaveBeenCalled();
  });

  it("thông báo một lần khi lượt chạy chuyển từ đang chạy sang xong hoặc lỗi", () => {
    const notify = vi.fn();
    const update = renderWith(notify, [
      { id: "a", status: "running" },
      { id: "b", status: "pending" },
    ]);

    update([
      { id: "a", status: "completed" },
      { id: "b", status: "running" },
    ]);
    update([
      { id: "a", status: "completed" },
      { id: "b", status: "failed" },
    ]);

    expect(notify).toHaveBeenCalledTimes(2);
    expect(notify).toHaveBeenNthCalledWith(1, { tone: "success", title: "a completed" });
    expect(notify).toHaveBeenNthCalledWith(2, { tone: "error", title: "b failed" });
  });

  it("chưa có dữ liệu (null) thì chưa ghi nhận gì", () => {
    const notify = vi.fn();
    const update = renderWith(notify, null);

    update([{ id: "a", status: "completed" }]);

    expect(notify).not.toHaveBeenCalled();
  });
});
