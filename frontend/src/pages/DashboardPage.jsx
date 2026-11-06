import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { describeError, formatDateTime } from "../formatting.js";
import { CATEGORY_LABELS, METRIC_LABELS, METRIC_STATUS_LABELS, formatScore } from "../metricLabels.js";
import { listEvaluations } from "../services/api/evaluationApi.js";

const COLUMNS = ["behavior_correct", "recall_at_k", "mrr", "ndcg_at_k", "faithfulness", "answer_relevancy"];

// So sánh các lượt đánh giá đã hoàn tất. Chỉ so được khi cùng phiên bản dataset, nên bảng nhóm theo dataset version.
export default function DashboardPage() {
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    listEvaluations({ status: "completed", limit: 100 })
      .then((result) => setRuns(result.items))
      .catch((caught) => setError(describeError(caught)));
  }, []);

  if (error) {
    return (
      <div className="alert alert--error" role="alert">
        {error}
      </div>
    );
  }
  if (runs === null) return <p className="page-message">Đang tải…</p>;
  if (runs.length === 0) {
    return (
      <p className="empty-state">
        Chưa có lượt đánh giá nào hoàn tất. <Link to="/evaluations">Tạo lượt đánh giá</Link>.
      </p>
    );
  }

  const groups = new Map();
  for (const run of runs) {
    const key = run.dataset_version_id;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(run);
  }

  return (
    <section className="dashboard">
      <h1>Dashboard đánh giá</h1>
      <p className="hint">
        Mỗi bảng là một phiên bản dataset: chỉ so sánh các lượt trên cùng bộ câu hỏi. Chưa có baseline nên không tô màu đạt/không đạt; “—” là
        metric không áp dụng hoặc bị bỏ qua.
      </p>
      {[...groups.entries()].map(([versionId, groupRuns]) => (
        <section key={versionId} className="card">
          <h2>
            Dataset v{groupRuns[0].environment?.dataset_version?.version_number ?? "?"} ·{" "}
            {groupRuns[0].environment?.dataset_version?.cases ?? groupRuns[0].total_cases} câu
          </h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Lượt</th>
                  <th>Cấu hình</th>
                  {COLUMNS.map((name) => (
                    <th key={name} title={METRIC_LABELS[name]?.hint}>
                      {METRIC_LABELS[name]?.label ?? name}
                    </th>
                  ))}
                  <th>Lỗi chính</th>
                </tr>
              </thead>
              <tbody>
                {groupRuns.map((run) => (
                  <DashboardRow key={run.id} run={run} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </section>
  );
}

function DashboardRow({ run }) {
  const config = run.environment?.model_configuration ?? {};
  const byName = Object.fromEntries(run.aggregate_metrics.map((metric) => [metric.metric_name, metric]));
  const topCategory = Object.entries(run.categories ?? {})
    .filter(([category]) => category !== "ok")
    .sort((a, b) => b[1] - a[1])[0];

  return (
    <tr>
      <td>{formatDateTime(run.created_at)}</td>
      <td className="cell-wrap">
        {config.llm_model} · top_k={config.top_k} · {config.prompt_version}
      </td>
      {COLUMNS.map((name) => {
        const metric = byName[name];
        if (!metric) return <td key={name}>—</td>;
        if (metric.status !== "computed") return <td key={name} className="muted">{METRIC_STATUS_LABELS[metric.status] ?? metric.status}</td>;
        return (
          <td key={name}>
            <span className="score-cell">
              <span className="score-cell__bar" style={{ width: `${Math.max(0, Math.min(1, metric.value)) * 100}%` }} aria-hidden="true" />
              <span className="score-cell__value">{formatScore(metric.value)}</span>
            </span>
          </td>
        );
      })}
      <td>{topCategory ? `${CATEGORY_LABELS[topCategory[0]] ?? topCategory[0]} (${topCategory[1]})` : "—"}</td>
    </tr>
  );
}
