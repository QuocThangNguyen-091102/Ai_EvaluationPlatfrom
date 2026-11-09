// Lucian UX/UI Prompt #269 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#269
import { useEffect, useRef, useState } from "react";

import "./ConfirmDeleteDialog.css";

/**
 * Hộp xác nhận xóa phải gõ đúng tên: nút Xóa chỉ bật khi gõ khớp hoàn toàn; phần tên đã gõ đúng tô đỏ dần, gõ sai một
 * ký tự thì ô nhập rung. Esc hoặc Hủy để đóng.
 *
 * Khác mẫu: bỏ hiệu ứng thẻ vỡ vụn và nút Hoàn tác, vì xóa ở backend là vĩnh viễn; nút Hoàn tác sẽ là một lời hứa sai.
 */
export default function ConfirmDeleteDialog({ name, title, description, onCancel, onConfirm }) {
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => inputRef.current?.focus(), []);

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onCancel]);

  let matched = 0;
  while (matched < typed.length && matched < name.length && typed[matched] === name[matched]) matched += 1;

  function handleChange(event) {
    const next = event.target.value;
    const input = inputRef.current;
    let nextMatched = 0;
    while (nextMatched < next.length && nextMatched < name.length && next[nextMatched] === name[nextMatched]) nextMatched += 1;
    // Rung chỉ khi vừa gõ thêm một ký tự sai (xóa bớt thì không rung).
    if (next.length > typed.length && nextMatched < next.length && input) {
      input.classList.remove("is-shake");
      void input.offsetWidth;
      input.classList.add("is-shake");
    }
    setTyped(next);
  }

  async function confirm() {
    if (typed !== name || busy) return;
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="confirm-delete">
      <div className="confirm-delete__dim" aria-hidden="true" onClick={onCancel} />
      <div className="confirm-delete__dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-delete-title" aria-describedby="confirm-delete-desc">
        <h4 id="confirm-delete-title">
          <i aria-hidden="true">!</i>
          {title}
        </h4>
        <p id="confirm-delete-desc">{description} Gõ đúng tên bên dưới để xác nhận.</p>
        <div className="confirm-delete__name" aria-hidden="true">
          {[...name].map((char, index) => (
            <span key={index} className={index < matched ? "is-ok" : undefined}>
              {char}
            </span>
          ))}
        </div>
        <input
          ref={inputRef}
          className="confirm-delete__input"
          aria-label={`Gõ tên "${name}" để xác nhận`}
          autoComplete="off"
          spellCheck="false"
          value={typed}
          onChange={handleChange}
          onKeyDown={(event) => event.key === "Enter" && confirm()}
        />
        <div className="confirm-delete__actions">
          <button type="button" className="confirm-delete__cancel" onClick={onCancel}>
            Hủy
          </button>
          <button type="button" className="confirm-delete__go" disabled={typed !== name || busy} onClick={confirm}>
            {busy ? "Đang xóa…" : "Xóa vĩnh viễn"}
          </button>
        </div>
      </div>
    </div>
  );
}
