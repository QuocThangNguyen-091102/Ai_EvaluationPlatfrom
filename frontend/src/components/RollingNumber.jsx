// Lucian UX/UI Prompt #098 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#098
// Chỉ lấy phần chữ số cuộn của mẫu; bỏ đường xu hướng vì hệ thống không lưu số liệu theo thời gian.
import { useEffect, useState } from "react";

import "./RollingNumber.css";

const DIGITS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];

/**
 * Số nguyên cuộn từ 0 lên giá trị thật khi xuất hiện; về sau đổi giá trị thì chỉ các chữ số khác đi mới cuộn.
 * Giá trị không phải số (ví dụ "…" khi đang tải, "?" khi lỗi) hiển thị nguyên dạng chữ.
 */
export default function RollingNumber({ value }) {
  const [shown, setShown] = useState(null);

  // Khung hình đầu vẽ toàn số 0, khung sau mới đặt giá trị thật để transition chạy (cuộn lên từ 0, như mẫu).
  useEffect(() => {
    if (!Number.isInteger(value)) return undefined;
    const frame = requestAnimationFrame(() => setShown(value));
    return () => cancelAnimationFrame(frame);
  }, [value]);

  if (!Number.isInteger(value)) return <span className="rolling-number">{value}</span>;

  const target = String(value);
  const current = shown === null ? "0".repeat(target.length) : String(shown).padStart(target.length, "0");

  return (
    <span className="rolling-number">
      <span className="visually-hidden">{target}</span>
      <span className="rolling-number__digits" aria-hidden="true">
        {[...target].map((_, index) => (
          <span key={target.length - index} className="rolling-number__column" style={{ "--d": Number(current[index] ?? 0), "--i": index }}>
            {DIGITS.map((digit) => (
              <span key={digit}>{digit}</span>
            ))}
          </span>
        ))}
      </span>
    </span>
  );
}
