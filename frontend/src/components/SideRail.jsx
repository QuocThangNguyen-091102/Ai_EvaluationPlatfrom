// Lucian UX/UI Prompt #040 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#040
import { useLayoutEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

import "./SideRail.css";

const WIDE_KEY = "ai-eval.rail-wide";

// Icon nét 24×24 theo phong cách của mẫu. "Hỏi đáp" và "Dashboard" lấy nguyên hình của mẫu (Messages, Projects).
const ICONS = {
  documents: (
    <path d="M7 3.5h6.5L18 8v11.5a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1v-15a1 1 0 0 1 1-1zM13 3.5V8h5M9 13h6M9 16.5h4" />
  ),
  chat: <path d="M5 5.5h14a1 1 0 0 1 1 1V16a1 1 0 0 1-1 1h-7l-4.5 3.5V17H5a1 1 0 0 1-1-1V6.5a1 1 0 0 1 1-1z" />,
  datasets: (
    <path d="M12 4c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3zM4 7v5c0 1.7 3.6 3 8 3s8-1.3 8-3V7M4 12v5c0 1.7 3.6 3 8 3s8-1.3 8-3v-5" />
  ),
  evaluations: (
    <path d="M8 5.5H6.5a1 1 0 0 0-1 1V19a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1V6.5a1 1 0 0 0-1-1H16M9 3.5h6v3H9zM9 13l2 2 4-4.5" />
  ),
  security: <path d="M12 3.5l7 2.8v5.4c0 4.3-3 7.4-7 8.8-4-1.4-7-4.5-7-8.8V6.3zM9 12l2 2 4-4" />,
  benchmarks: <path d="M5 19.5V13M12 19.5V8M19 19.5V4.5M3.5 19.5h17" />,
  dashboard: (
    <>
      <rect x="4" y="4" width="7" height="7" rx="2" />
      <rect x="13" y="4" width="7" height="7" rx="2" />
      <rect x="4" y="13" width="7" height="7" rx="2" />
      <rect x="13" y="13" width="7" height="7" rx="2" />
    </>
  ),
  logout: <path d="M14 4.5h4a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-4M10 16l-4-4 4-4M6 12h9" />,
};

const ITEMS = [
  { to: "/documents", label: "Tài liệu", icon: "documents" },
  { to: "/chat", label: "Hỏi đáp", icon: "chat" },
  { to: "/datasets", label: "Dataset", icon: "datasets" },
  { to: "/evaluations", label: "Đánh giá", icon: "evaluations" },
  { to: "/security", label: "Bảo mật", icon: "security" },
  { to: "/benchmarks", label: "Benchmark", icon: "benchmarks" },
  { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
];

// Trạng thái mở rộng là tiện ích riêng của từng trình duyệt; đọc hoặc ghi lỗi thì dùng mặc định (thu gọn).
function readWide() {
  try {
    return window.localStorage.getItem(WIDE_KEY) === "1";
  } catch {
    return false;
  }
}

function storeWide(wide) {
  try {
    window.localStorage.setItem(WIDE_KEY, wide ? "1" : "0");
  } catch {
    // Không lưu được thì lần sau mở lại ở trạng thái thu gọn.
  }
}

function Icon({ name }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}

export default function SideRail({ email, onLogout }) {
  const [wide, setWide] = useState(readWide);
  const navRef = useRef(null);
  const highlightRef = useRef(null);
  const { pathname } = useLocation();

  // Vệt sáng trượt tới mục đang mở; NavLink tự gắn aria-current="page" cho mục đó.
  useLayoutEffect(() => {
    const active = navRef.current?.querySelector('a[aria-current="page"]');
    const highlight = highlightRef.current;
    if (!highlight) return;
    highlight.style.opacity = active ? "1" : "0";
    if (active) highlight.style.setProperty("--y", `${active.parentNode.offsetTop}px`);
  }, [pathname]);

  function toggle() {
    setWide((current) => {
      storeWide(!current);
      return !current;
    });
  }

  function moveFocus(event) {
    const step = event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;
    if (!step) return;
    const links = [...navRef.current.querySelectorAll(".side-rail__item")];
    const index = links.indexOf(document.activeElement);
    if (index < 0) return;
    event.preventDefault();
    links[(index + step + links.length) % links.length].focus();
  }

  return (
    <nav className={`side-rail${wide ? " side-rail--wide" : ""}`} aria-label="Điều hướng chính">
      <div className="side-rail__panel">
        <div className="side-rail__top">
          <span className="side-rail__logo" aria-hidden="true" />
          <span className="side-rail__name">AI Evaluation</span>
        </div>
        <button
          className="side-rail__toggle"
          type="button"
          aria-expanded={wide}
          aria-label={wide ? "Thu gọn menu" : "Mở rộng menu"}
          onClick={toggle}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M6 3.5L10.5 8 6 12.5" />
          </svg>
        </button>

        <ul className="side-rail__nav" ref={navRef} onKeyDown={moveFocus}>
          <li className="side-rail__highlight" role="presentation" ref={highlightRef} />
          {ITEMS.map((item, index) => (
            <li key={item.to}>
              <NavLink to={item.to} className="side-rail__item" style={{ "--i": index }} title={wide ? undefined : item.label}>
                <Icon name={item.icon} />
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
          <li style={{ marginTop: "auto" }}>
            <button type="button" className="side-rail__item" style={{ "--i": ITEMS.length }} onClick={onLogout} title={wide ? undefined : "Đăng xuất"}>
              <Icon name="logout" />
              <span>Đăng xuất</span>
            </button>
          </li>
        </ul>

        <div className="side-rail__me" title={email}>
          <span className="side-rail__avatar" aria-hidden="true">
            {email?.[0] ?? "?"}
          </span>
          <span className="side-rail__email">
            {email}
            <small>Đang đăng nhập</small>
          </span>
        </div>
      </div>
    </nav>
  );
}
