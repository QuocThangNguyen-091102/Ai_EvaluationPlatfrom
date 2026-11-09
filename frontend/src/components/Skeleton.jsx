// Lucian UX/UI Prompt #079 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#079
import "./Skeleton.css";

// Độ dài các dòng thay đổi để khung giống nội dung thật, không phải các thanh bằng nhau.
const LINE_WIDTHS = [
  ["62%", "38%"],
  ["74%", "44%"],
  ["55%", "30%"],
];

/**
 * Khung chờ trong lúc tải danh sách. Khi dữ liệu về, nơi dùng đặt class `skeleton-reveal` lên vùng chứa nội dung để
 * các phần tử con hiện dần từ trên xuống.
 */
export default function Skeleton({ rows = 4, label = "Đang tải…" }) {
  return (
    <div className="skeleton" role="status" aria-busy="true" aria-label={label}>
      {Array.from({ length: rows }, (_, index) => {
        const [first, second] = LINE_WIDTHS[index % LINE_WIDTHS.length];
        return (
          <div key={index} className="skeleton__row" aria-hidden="true">
            <span className="skeleton__block skeleton__block--icon" />
            <span className="skeleton__lines">
              <span className="skeleton__block" style={{ width: first }} />
              <span className="skeleton__block" style={{ width: second }} />
            </span>
          </div>
        );
      })}
    </div>
  );
}
