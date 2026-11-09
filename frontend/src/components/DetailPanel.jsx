// Lucian UX/UI Prompt #273 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#273
import { useEffect, useRef } from "react";

import "./DetailPanel.css";

const ARROW_UP = <path d="M2 7l3.5-3.5L9 7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />;
const ARROW_DOWN = <path d="M2 4l3.5 3.5L9 4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />;
const CROSS = <path d="M2.5 2.5l6 6M8.5 2.5l-6 6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />;

function isTyping(target) {
  return target instanceof HTMLElement && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
}

/**
 * Panel chi tiết trượt ra từ mép phải cho một dòng trong danh sách. Mũi tên trên thanh công cụ hoặc phím J/K chuyển
 * sang mục sau/trước (nội dung trượt theo hướng đi), Esc hoặc bấm ra ngoài thì đóng và trả focus về dòng đã mở.
 *
 * `index` là vị trí mục đang mở (null khi đóng); `direction` là 1 (xuống), -1 (lên) hoặc 0 (mở mới).
 */
export default function DetailPanel({ index, count, direction = 0, label, itemLabel, onMove, onClose, children }) {
  const open = index !== null && index !== undefined;
  const panelRef = useRef(null);
  // Giữ nội dung lần mở cuối để panel trượt ra cùng nội dung thay vì trống trơn (như mẫu).
  const lastShown = useRef(null);
  if (open) lastShown.current = { index, direction, children };
  const shown = open ? { index, direction, children } : lastShown.current;

  useEffect(() => {
    if (!open) return undefined;
    panelRef.current?.focus({ preventScroll: true });
    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
      if (isTyping(event.target) || event.ctrlKey || event.metaKey || event.altKey) return;
      if ((event.key === "j" || event.key === "J") && index < count - 1) onMove(index + 1, 1);
      if ((event.key === "k" || event.key === "K") && index > 0) onMove(index - 1, -1);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, index, count, onMove, onClose]);

  return (
    <>
      <div className={`detail-panel__overlay${open ? " is-open" : ""}`} aria-hidden="true" onClick={onClose} />
      <aside
        ref={panelRef}
        className={`detail-panel${open ? " is-open" : ""}`}
        role="dialog"
        aria-label={label}
        aria-hidden={!open}
        tabIndex={-1}
      >
        {shown && (
          <>
            <div className="detail-panel__toolbar">
              <button type="button" aria-label={`${itemLabel} trước (K)`} disabled={!open || index === 0} onClick={() => onMove(index - 1, -1)}>
                <svg viewBox="0 0 11 11" aria-hidden="true">{ARROW_UP}</svg>
              </button>
              <button type="button" aria-label={`${itemLabel} sau (J)`} disabled={!open || index === count - 1} onClick={() => onMove(index + 1, 1)}>
                <svg viewBox="0 0 11 11" aria-hidden="true">{ARROW_DOWN}</svg>
              </button>
              <span className="detail-panel__position">
                {shown.index + 1} / {count}
              </span>
              <button type="button" aria-label="Đóng (Esc)" onClick={onClose}>
                <svg viewBox="0 0 11 11" aria-hidden="true">{CROSS}</svg>
              </button>
            </div>
            <div className="detail-panel__body" aria-live="polite">
              <div key={shown.index} className="detail-panel__page" data-direction={shown.direction}>
                {shown.children}
              </div>
            </div>
          </>
        )}
      </aside>
    </>
  );
}
