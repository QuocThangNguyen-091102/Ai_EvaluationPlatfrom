// Lucian UX/UI Prompt #155 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#155
import { useState } from "react";

import { formatLatency } from "../formatting.js";
import { METRIC_LABELS, formatScore } from "../metricLabels.js";
import "./BenchmarkScatter.css";

// Chừa lề để điểm ở biên không bị cắt nửa.
const EDGE_PERCENT = 6;

function metricValue(variant, name) {
  const metric = variant.aggregate_metrics.find((item) => item.metric_name === name);
  return metric?.status === "computed" && metric.value != null ? metric.value : null;
}

/**
 * Mỗi cấu hình của benchmark là một điểm: ngang là độ trễ p50, dọc là metric chất lượng được chọn (thang 0–1).
 * Bấm một điểm để xem số của cấu hình đó.
 *
 * Khác mẫu: mẫu dùng trục chi phí và nút lọc "≤ 55¢". Ở đây trục ngang là độ trễ vì model chạy cục bộ có chi phí 0
 * (mọi điểm sẽ dồn về một cột), và bỏ nút lọc vì đó là ngưỡng tùy ý khi chưa có baseline.
 */
export default function BenchmarkScatter({ benchmark, metrics }) {
  const available = metrics.filter((name) => benchmark.variants.some((variant) => metricValue(variant, name) !== null));
  const [metric, setMetric] = useState(available[0] ?? null);
  const [selected, setSelected] = useState(null);

  const chosen = available.includes(metric) ? metric : available[0];
  const points = benchmark.variants
    .map((variant) => ({ variant, latency: variant.usage?.latency_p50_ms, value: chosen ? metricValue(variant, chosen) : null }))
    .filter((point) => point.latency != null && point.value !== null);
  const missing = benchmark.variants.length - points.length;

  if (!chosen || points.length === 0) {
    return <p className="muted">Chưa có cấu hình nào đủ cả độ trễ và metric để vẽ.</p>;
  }

  const maxLatency = Math.max(...points.map((point) => point.latency)) * 1.1 || 1;
  const toPercent = (fraction) => EDGE_PERCENT + fraction * (100 - EDGE_PERCENT * 2);
  const current = points.find((point) => point.variant.evaluation_run_id === selected);
  const label = METRIC_LABELS[chosen]?.label ?? chosen;

  return (
    <div className="benchmark-scatter">
      <div className="benchmark-scatter__head">
        <small className="muted">
          {label} theo độ trễ p50 · {benchmark.varied_variable}
        </small>
        <label className="chat-config">
          Metric
          <select value={chosen} onChange={(event) => setMetric(event.target.value)}>
            {available.map((name) => (
              <option key={name} value={name}>
                {METRIC_LABELS[name]?.label ?? name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="benchmark-scatter__plot" role="group" aria-label={`${label} và độ trễ p50 theo từng cấu hình`}>
        {points.map(({ variant, latency, value }) => {
          const left = `${toPercent(latency / maxLatency)}%`;
          const bottom = `${toPercent(value)}%`;
          const name = String(variant.varied_value);
          const pressed = selected === variant.evaluation_run_id;
          return (
            <span key={variant.evaluation_run_id}>
              <button
                type="button"
                className="benchmark-scatter__point"
                style={{ left, bottom }}
                aria-pressed={pressed}
                aria-label={`${benchmark.varied_variable} = ${name}: ${label} ${formatScore(value)}, p50 ${formatLatency(latency)}`}
                onClick={() => setSelected(pressed ? null : variant.evaluation_run_id)}
              />
              <span className="benchmark-scatter__label" style={{ left, bottom }} aria-hidden="true">
                {name}
              </span>
            </span>
          );
        })}
      </div>
      <div className="benchmark-scatter__axis">
        <small>{label} ↑ (0–1)</small>
        <small>Độ trễ p50 → (tối đa {formatLatency(Math.round(maxLatency / 1.1))})</small>
      </div>
      <p className="benchmark-scatter__status" aria-live="polite">
        {current ? (
          <>
            {benchmark.varied_variable} = {String(current.variant.varied_value)} ·{" "}
            <b>
              {label} {formatScore(current.value)} / p50 {formatLatency(current.latency)}
            </b>
          </>
        ) : (
          <>
            {points.length} cấu hình
            {missing > 0 && ` · ${missing} cấu hình chưa đủ dữ liệu để vẽ`}
          </>
        )}
      </p>
    </div>
  );
}
