// Lucian UX/UI Prompt #070 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#070
import { useEffect, useLayoutEffect, useRef, useState } from "react";

import "./ToastStack.css";

const DURATION_MS = 4500;
const SWIPE_DISMISS_PX = 90;

const TONE_COLORS = { success: "var(--ux-mint)", error: "var(--ux-danger)", info: "var(--ux-accent)" };

const ICONS = {
  success: <path d="M4 9.4l3.2 3.2L14 5.6" />,
  error: <path d="M9 5v5M9 13h.01" />,
  info: <path d="M3.5 4.5h11v7h-6l-3 2.5v-2.5h-2z" />,
};

/**
 * Chồng toast: toast mới trồi lên phía trước, toast cũ thu nhỏ lùi ra sau. Di chuột hoặc focus vào thì chồng xòe
 * thành danh sách và ngừng đếm giờ; vuốt ngang để bỏ một toast. Chỉ toast phía trước đếm ngược để tự ẩn.
 */
export default function ToastStack({ toasts, onDismiss }) {
  const [open, setOpen] = useState(false);
  const zoneRef = useRef(null);
  const elements = useRef(new Map());
  const remaining = useRef(new Map());
  const entered = useRef(new Set());
  const drag = useRef(null);

  const active = toasts.filter((toast) => !toast.leaving);
  const activeRef = useRef(active);
  const openRef = useRef(open);
  activeRef.current = active;
  openRef.current = open;

  if (open && active.length === 0) setOpen(false);

  // Vị trí từng toast phụ thuộc chiều cao thật của toast phía trước, nên tính sau khi DOM đã có (như mẫu).
  useLayoutEffect(() => {
    for (const toast of toasts) {
      const element = elements.current.get(toast.id);
      if (element && !entered.current.has(toast.id)) {
        entered.current.add(toast.id);
        void element.offsetWidth;
        element.classList.remove("toast--enter");
      }
    }
    let offset = 0;
    active.forEach((toast, index) => {
      const element = elements.current.get(toast.id);
      if (!element) return;
      element.classList.toggle("toast--back", !open && index > 0);
      if (open) {
        element.style.setProperty("--y", `${-offset}px`);
        element.style.setProperty("--s", "1");
        element.style.setProperty("--o", "1");
        offset += element.offsetHeight + 8;
      } else {
        element.style.setProperty("--y", `${-(index * 14)}px`);
        element.style.setProperty("--s", (1 - index * 0.06).toFixed(2));
        element.style.setProperty("--o", index > 2 ? "0" : "1");
      }
      element.style.zIndex = String(50 - index);
      element.inert = !open && index > 0;
    });
    // Khi xòe, vùng chứa phủ cả khe giữa các toast để rê chuột qua khe không làm chồng gập lại.
    if (zoneRef.current) zoneRef.current.style.height = open ? `${Math.max(0, offset - 8)}px` : "0px";
  });

  // Một vòng requestAnimationFrame đếm ngược cho toast phía trước; dừng khi chồng đang xòe.
  const hasToasts = active.length > 0;
  useEffect(() => {
    if (!hasToasts) return undefined;
    let frame = 0;
    let last = performance.now();
    function tick(now) {
      const elapsed = now - last;
      last = now;
      const front = activeRef.current[0];
      if (front && !openRef.current && !drag.current) {
        const left = (remaining.current.get(front.id) ?? DURATION_MS) - elapsed;
        remaining.current.set(front.id, left);
        elements.current.get(front.id)?.style.setProperty("--left", Math.max(0, left / DURATION_MS).toFixed(3));
        if (left <= 0) {
          remaining.current.set(front.id, Infinity);
          onDismiss(front.id);
        }
      }
      frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [hasToasts, onDismiss]);

  function startDrag(event, id) {
    if (event.target.closest("button")) return;
    const element = elements.current.get(id);
    drag.current = { id, startX: event.clientX, dx: 0 };
    element.setPointerCapture?.(event.pointerId);
    element.classList.add("toast--drag");
  }

  function moveDrag(event) {
    const current = drag.current;
    if (!current) return;
    current.dx = event.clientX - current.startX;
    const element = elements.current.get(current.id);
    element.style.setProperty("--dx", `${current.dx}px`);
    element.style.setProperty("--o", String(Math.max(0.2, 1 - Math.abs(current.dx) / 260)));
  }

  function endDrag() {
    const current = drag.current;
    if (!current) return;
    drag.current = null;
    const element = elements.current.get(current.id);
    element.classList.remove("toast--drag");
    if (Math.abs(current.dx) > SWIPE_DISMISS_PX) {
      onDismiss(current.id, current.dx > 0 ? 1 : -1);
    } else {
      element.style.setProperty("--dx", "0px");
      element.style.setProperty("--o", "1");
      // Bấm (không kéo) vào thân toast thì xòe hoặc gập chồng, như mẫu.
      if (Math.abs(current.dx) < 5 && activeRef.current.length > 1) setOpen((value) => !value);
    }
  }

  function handleBlur(event) {
    if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
  }

  return (
    <div
      className="toast-stack"
      role="region"
      aria-label="Thông báo"
      onFocus={() => setOpen(true)}
      onBlur={handleBlur}
      onPointerLeave={(event) => event.pointerType === "mouse" && setOpen(false)}
    >
      <div className={`toast-stack__zone${open ? " toast-stack__zone--open" : ""}`} ref={zoneRef} />
      {toasts.map((toast) => {
        const classes = [
          "toast",
          !entered.current.has(toast.id) && "toast--enter",
          toast.leaving && "toast--leave",
          toast.leaving && toast.direction !== 0 && "toast--side",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <div
            key={toast.id}
            ref={(element) => {
              if (element) elements.current.set(toast.id, element);
              else elements.current.delete(toast.id);
            }}
            className={classes}
            style={{ "--c": TONE_COLORS[toast.tone], "--dir": toast.direction || 1 }}
            role={toast.tone === "error" ? "alert" : "status"}
            onPointerDown={(event) => startDrag(event, toast.id)}
            onPointerMove={moveDrag}
            onPointerUp={endDrag}
            onPointerCancel={endDrag}
            onPointerEnter={(event) => event.pointerType === "mouse" && !toast.leaving && setOpen(true)}
          >
            <span className="toast__icon" aria-hidden="true">
              <svg viewBox="0 0 18 18">{ICONS[toast.tone]}</svg>
            </span>
            <span className="toast__text">
              <b>{toast.title}</b>
              {toast.detail && <small>{toast.detail}</small>}
            </span>
            <button className="toast__close" type="button" aria-label="Đóng thông báo" onClick={() => onDismiss(toast.id)}>
              <svg viewBox="0 0 14 14" aria-hidden="true">
                <path d="M3.5 3.5l7 7M10.5 3.5l-7 7" />
              </svg>
            </button>
            <span className="toast__timer" aria-hidden="true" />
          </div>
        );
      })}
    </div>
  );
}
