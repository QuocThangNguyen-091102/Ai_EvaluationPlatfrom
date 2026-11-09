// Lucian UX/UI Prompt #008 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#008
import { useEffect, useRef, useState } from "react";

import "./CopyButton.css";

const COPIED_MS = 1800;

// Clipboard API chỉ có trong secure context (HTTPS hoặc localhost); thiếu thì dùng cách cũ qua textarea ẩn.
async function writeClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  const ok = document.execCommand("copy");
  area.remove();
  if (!ok) throw new Error("copy failed");
}

export default function CopyButton({ text, label = "Copy" }) {
  const [state, setState] = useState("idle");
  const timer = useRef(0);

  useEffect(() => () => clearTimeout(timer.current), []);

  async function copy() {
    clearTimeout(timer.current);
    try {
      await writeClipboard(text);
      setState("copied");
    } catch {
      setState("failed");
    }
    timer.current = setTimeout(() => setState("idle"), COPIED_MS);
  }

  return (
    <button type="button" className={`copy-button${state === "copied" ? " copy-button--copied" : ""}`} aria-label={label} onClick={copy}>
      <svg className="copy-button__copy" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="8.5" y="8.5" width="11" height="11" rx="2.5" />
        <path d="M15.5 8.5V6.5a2 2 0 0 0-2-2h-7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h2" />
      </svg>
      <svg className="copy-button__check" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5.5 12.5l4.2 4.2L18.5 8" />
      </svg>
      <span className="copy-button__tip" role="status">
        {state === "copied" ? "Đã copy" : state === "failed" ? "Không copy được" : ""}
      </span>
    </button>
  );
}
