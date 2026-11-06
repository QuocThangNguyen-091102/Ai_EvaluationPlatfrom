import { METRIC_LABELS, METRIC_STATUS_LABELS, formatScore, metricName } from "../metricLabels.js";

// Biểu đồ thanh ngang bằng CSS cho metric thang 0–1. Metric bị bỏ qua/không chấm được thì ghi chữ, không vẽ thanh 0.
export default function MetricBars({ metrics }) {
  if (!metrics?.length) return <p className="muted">Chưa có metric.</p>;
  return (
    <dl className="metric-bars">
      {metrics.map((metric) => {
        const key = `${metric.metric_name}-${metric.k ?? ""}`;
        const computed = metric.status === "computed" && metric.value != null;
        const percent = computed ? Math.max(0, Math.min(1, metric.value)) * 100 : 0;
        const cases = metric.details?.cases;
        return (
          <div className="metric-bars__row" key={key}>
            <dt title={METRIC_LABELS[metric.metric_name]?.hint}>
              {metricName(metric)}
              {metric.method === "llm_judge" && <span className="metric-bars__method"> (judge)</span>}
            </dt>
            <dd>
              {computed ? (
                <>
                  <span className="metric-bars__track" aria-hidden="true">
                    <span className="metric-bars__fill" style={{ width: `${percent}%` }} />
                  </span>
                  <span className="metric-bars__value">{formatScore(metric.value)}</span>
                  {cases != null && <span className="muted metric-bars__cases">n={cases}</span>}
                </>
              ) : (
                <span className="muted">{METRIC_STATUS_LABELS[metric.status] ?? metric.status}</span>
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
