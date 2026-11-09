// Lucian UX/UI Prompt #036 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#036
// Nút con mắt kết hợp với #062 (Sign-in card feedback) · cùng giấy phép MIT.
import { useId, useState } from "react";

import "./PasswordField.css";

const MIN_LENGTH = 8;

// Chỉ độ dài là máy chủ bắt buộc (PASSWORD_MIN_LENGTH, mặc định 8); ba điều kiện còn lại là gợi ý để mật khẩu mạnh hơn.
const RULES = [
  { key: "length", label: `Ít nhất ${MIN_LENGTH} ký tự (bắt buộc)`, test: (value) => value.length >= MIN_LENGTH },
  { key: "upper", label: "Có chữ hoa", test: (value) => /\p{Lu}/u.test(value) },
  { key: "digit", label: "Có chữ số", test: (value) => /\d/.test(value) },
  { key: "symbol", label: "Có ký tự đặc biệt", test: (value) => /[^\p{L}\p{N}]/u.test(value) },
];

const LEVELS = [
  { word: "Nhập mật khẩu", color: "var(--ux-line-2)" },
  { word: "Yếu", color: "var(--danger)" },
  { word: "Tạm được", color: "#F07A3E" },
  { word: "Khá", color: "#E8B417" },
  { word: "Mạnh", color: "var(--ok)" },
];

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <g className="password-field__lid">
        <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
      </g>
      <circle className="password-field__pupil" cx="12" cy="12" r="3" />
      <path className="password-field__slash" d="M4 4l16 16" />
    </svg>
  );
}

/**
 * Ô mật khẩu có nút con mắt (mi mắt mở ra khi hiện mật khẩu). `showStrength` bật thanh độ mạnh 4 nấc và danh sách
 * điều kiện, dùng khi đăng ký.
 */
export default function PasswordField({ label, value, onChange, autoComplete, showStrength = false }) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  const passed = RULES.map((rule) => rule.test(value));
  const score = passed.filter(Boolean).length;
  const level = value ? LEVELS[Math.max(1, score)] : LEVELS[0];

  return (
    <div
      className={`password-field${showStrength ? " password-field--strength" : ""}${value ? " has-value" : ""}${visible ? " is-show" : ""}`}
      style={{ "--lv": level.color }}
    >
      <label htmlFor={id}>{label}</label>
      <div className="password-field__box">
        <input
          id={id}
          type={visible ? "text" : "password"}
          name="password"
          autoComplete={autoComplete}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-describedby={showStrength ? `${id}-strength ${id}-rules` : undefined}
          required
        />
        <button
          type="button"
          className="password-field__eye"
          aria-pressed={visible}
          aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          onClick={() => setVisible((current) => !current)}
        >
          <EyeIcon />
        </button>
      </div>

      {showStrength && (
        <>
          <div className="password-field__meter" aria-hidden="true">
            {[1, 2, 3, 4].map((step) => (
              <i key={step} className={value && score >= step ? "on" : undefined} />
            ))}
          </div>
          <p className="password-field__level" id={`${id}-strength`}>
            <span>Độ mạnh</span>
            <b aria-live="polite">{level.word}</b>
          </p>
          <ul className="password-field__rules" id={`${id}-rules`}>
            {RULES.map((rule, index) => (
              <li key={rule.key} className={passed[index] ? "ok" : undefined}>
                <i aria-hidden="true">
                  <svg viewBox="0 0 20 20">
                    <path d="M5.5 10.5l3 3 6-6.5" />
                  </svg>
                </i>
                {rule.label}
                <span className="visually-hidden">{passed[index] ? ": đạt" : ": chưa đạt"}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
