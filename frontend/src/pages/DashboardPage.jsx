import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { describeError, formatDateTime } from "../formatting.js";
import { CATEGORY_LABELS, METRIC_LABELS, METRIC_STATUS_LABELS, formatScore } from "../metricLabels.js";
import { listBenchmarks } from "../services/api/benchmarkApi.js";
import { listSessions } from "../services/api/chatApi.js";
import { listDatasets } from "../services/api/datasetApi.js";
import { listDocuments } from "../services/api/documentApi.js";
import { listEvaluations } from "../services/api/evaluationApi.js";
import { listSecurityRuns } from "../services/api/securityApi.js";

const COLUMNS = ["behavior_correct", "recall_at_k", "mrr", "ndcg_at_k", "context_precision", "context_recall", "faithfulness", "answer_relevancy"];

const OVERVIEW = [
  { key: "documents", label: "Tài liệu", to: "/documents", load: () => listDocuments({ limit: 1 }) },
  { key: "chats", label: "Phiên hỏi đáp", to: "/chat", load: () => listSessions({ limit: 1 }) },
  { key: "datasets", label: "Dataset", to: "/datasets", load: () => listDatasets() },
  { key: "evaluations", label: "Lượt đánh giá", to: "/evaluations", load: () => listEvaluations({ limit: 1 }) },
  { key: "security", label: "Lượt kiểm thử bảo mật", to: "/security", load: () => listSecurityRuns() },
  { key: "benchmarks", label: "Benchmark", to: "/benchmarks", load: () => listBenchmarks() },
];

export default function DashboardPage() {
  return (
    <section className="dashboard">
      <h1>Dashboard</h1>
      <OverviewStats />
      <EvaluationComparison />
    </section>
  );
}

// Mỗi ô tải độc lập: một API lỗi chỉ làm ô đó hiện "?", không làm hỏng cả trang.
function OverviewStats() {
  const [counts, setCounts] = useState({});
  const [latestSecurity, setLatestSecurity] = useState(null);

  useEffect(() => {
    for (const item of OVERVIEW) {
      item
        .load()
        .then((result) => {
          setCounts((current) => ({ ...current, [item.key]: result.total ?? result.items?.length ?? 0 }));
          if (item.key === "security") setLatestSecurity(result.items?.find((run) => run.status === "completed") ?? null);
        })
        .catch(() => setCounts((current) => ({ ...current, [item.key]: "?" })));
    }
  }, []);

  const fails = latestSecurity?.summary?.by_status?.fail ?? 0;
  return (
    <section aria-label="Tổng quan">
      <ul className="overview-stats">
        {OVERVIEW.map((item) => (
          <li key={item.key}>
            <Link to={item.to} className="overview-stat">
              <span className="overview-stat__value">{counts[item.key] ?? "…"}</span>
              <span className="overview-stat__label">{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>
      {latestSecurity && (
        <p className={fails ? "alert alert--error" : "notice"}>
          Kiểm thử bảo mật gần nhất ({formatDateTime(latestSecurity.created_at)}): {latestSecurity.summary?.by_status?.pass ?? 0} đạt, {fails} không
          đạt, {latestSecurity.summary?.by_status?.skipped ?? 0} bỏ qua. <Link to="/security">Xem chi tiết</Link>
        </p>
      )}
    </section>
  );
}

// So sánh các lượt đánh giá đã hoàn tất. Chỉ so được khi cùng phiên bản dataset, nên bảng nhóm theo dataset version.
function EvaluationComparison() {
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
      <h2>So sánh các lượt đánh giá</h2>
      <p className="hint">
        Mỗi bảng là một phiên bản dataset: chỉ so sánh các lượt trên cùng bộ câu hỏi. Chưa có baseline nên không tô màu đạt/không đạt; “—” là
        metric không áp dụng hoặc bị bỏ qua.
      </p>
      {[...groups.entries()].map(([versionId, groupRuns]) => (
        <section key={versionId} className="card">
          <h2>
            Dataset phiên bản {groupRuns[0].environment?.dataset_version?.version_number ?? "?"} ·{" "}
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
