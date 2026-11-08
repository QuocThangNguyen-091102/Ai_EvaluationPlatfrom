// Lucian UX/UI Prompt #083 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#083
import { useState } from "react";

import { formatClock, formatDuration } from "../formatting.js";
import { RUN_STATUS_LABELS } from "../metricLabels.js";
import "./RunProgress.css";

const UNFINISHED = new Set(["pending", "running"]);

const PILL_COLORS = {
  pending: "var(--ux-warn)",
  running: "var(--ux-accent)",
  completed: "var(--ux-mint)",
  failed: "var(--ux-danger)",
};

// Mỗi dòng nhật ký là một mốc có thật của lượt chạy (created_at, started_at, finished_at), không phải bước giả lập.
function buildLog({ status, completed, total, unit, createdAt, startedAt, finishedAt }) {
  const lines = [{ key: "queued", text: "Đã vào hàng đợi", time: createdAt, state: status === "pending" ? "active" : "ok" }];
  if (status === "running") {
    lines.push({ key: "run", text: `Đang chạy ${completed}/${total} ${unit}`, time: startedAt, state: "active" });
  }
  if (status === "completed") {
    lines.push({ key: "run", text: `Đã chạy ${completed}/${total} ${unit}`, time: startedAt, state: "ok" });
    lines.push({ key: "end", text: "Hoàn tất", time: finishedAt, state: "ok" });
  }
  if (status === "failed") {
    lines.push({ key: "end", text: `Dừng ở ${completed}/${total} ${unit}`, time: finishedAt, state: "error" });
  }
  return lines;
}

function describeMeta({ status, completed, total, unit, failed, startedAt, finishedAt }) {
  const duration = startedAt && finishedAt ? formatDuration(startedAt, finishedAt) : "";
  const failedNote = failed > 0 ? ` · ${failed} lỗi` : "";
  if (status === "pending") return ["Đang chờ tới lượt chạy", ""];
  if (status === "running") return [`${completed}/${total} ${unit}${failedNote}`, `${total ? Math.round((completed / total) * 100) : 0}%`];
  if (status === "completed") return [`Đã chạy xong ${total} ${unit}${failedNote}`, duration];
  return [`Dừng ở ${completed}/${total} ${unit}`, duration];
}

/**
 * Tiến độ của một lượt chạy nền (đánh giá, kiểm thử bảo mật, benchmark).
 *
 * Chỉ hiện khi lượt chạy chưa xong. Nếu lượt chạy kết thúc trong lúc đang xem thì giữ lại trạng thái cuối
 * (Hoàn tất hoặc Lỗi) để người dùng thấy được kết quả. Nơi dùng nên đặt `key` theo id lượt chạy, để khi chuyển
 * sang lượt khác thì trạng thái này được tính lại từ đầu.
 *
 * `completed` là số mục đã xử lý xong (kể cả mục lỗi); `failed` là số mục lỗi trong đó, nếu có.
 */
export default function RunProgress({ status, completed, total, unit, failed = 0, createdAt, startedAt, finishedAt }) {
  const unfinished = UNFINISHED.has(status);
  const [watchedWhileRunning, setWatchedWhileRunning] = useState(unfinished);
  if (unfinished && !watchedWhileRunning) setWatchedWhileRunning(true);
  if (!unfinished && !watchedWhileRunning) return null;

  const run = { status, completed, total, unit, failed, createdAt, startedAt, finishedAt };
  const determinate = status !== "pending";
  const ratio = status === "completed" ? 1 : total ? completed / total : 0;
  const [metaLeft, metaRight] = describeMeta(run);
  const classes = [
    "run-progress",
    determinate && "run-progress--determinate",
    status === "completed" && "run-progress--done",
    status === "failed" && "run-progress--failed",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <section className={classes} aria-label="Tiến độ lượt chạy">
      <div className="run-progress__header">
        <i className="run-progress__icon" aria-hidden="true" />
        <span>
          <b className="run-progress__title">Tiến độ</b>
          <small className="run-progress__subtitle">
            {total} {unit}
            {startedAt && ` · bắt đầu ${formatClock(startedAt)}`}
          </small>
        </span>
        <span className="run-progress__pill" role="status" aria-live="polite" style={{ "--c": PILL_COLORS[status] }}>
          {RUN_STATUS_LABELS[status] ?? status}
        </span>
      </div>

      <div
        className="run-progress__track"
        role="progressbar"
        aria-label={`Tiến độ (${unit})`}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={determinate ? completed : undefined}
        aria-valuetext={determinate ? `${completed}/${total} ${unit}` : "Đang chờ"}
      >
        <span className="run-progress__segment run-progress__segment--a" aria-hidden="true" />
        <span className="run-progress__segment run-progress__segment--b" aria-hidden="true" />
        <span className="run-progress__fill" aria-hidden="true" style={{ "--p": ratio }} />
      </div>
      <div className="run-progress__meta">
        <span>{metaLeft}</span>
        <span>{metaRight}</span>
      </div>

      <ol className="run-progress__log" aria-label="Nhật ký lượt chạy">
        {buildLog(run).map((line) => (
          <li key={line.key} className={line.state === "active" ? undefined : `is-${line.state}`}>
            <span className="run-progress__mark" aria-hidden="true" />
            <time dateTime={line.time ?? undefined}>{line.time ? formatClock(line.time) : "--:--:--"}</time>
            <span>{line.text}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
