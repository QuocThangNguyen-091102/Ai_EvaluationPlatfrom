// Lucian UX/UI Prompt #263 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#263
// Chỉ lấy phần "đang suy nghĩ" của mẫu: vệt sáng quét qua dòng chữ xám. Bỏ tiêu đề gradient và các chip chọn màu.
import "./ThinkingText.css";

export default function ThinkingText({ children }) {
  return (
    <p className="thinking-text" role="status">
      <span className="thinking-text__sheen">{children}</span>
    </p>
  );
}
