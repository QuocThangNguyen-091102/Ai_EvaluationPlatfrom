import { useCallback, useEffect, useState } from "react";

import MetricBars from "../components/MetricBars.jsx";
import { describeError, formatCost, formatDateTime, formatLatency } from "../formatting.js";
import {
  CATEGORY_LABELS,
  METRIC_STATUS_LABELS,
  RUN_STATUS_LABELS,
  formatScore,
  metricName,
} from "../metricLabels.js";
import { listDatasets, listVersions } from "../services/api/datasetApi.js";
import { createEvaluation, downloadReport, getEvaluation, listEvaluations, listResults } from "../services/api/evaluationApi.js";
import { getCapabilities, listConfigurations } from "../services/api/modelConfigApi.js";

const POLL_MS = 2000;
const UNFINISHED = new Set(["pending", "running"]);

export default function EvaluationsPage() {
  const [runs, setRuns] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);

  const loadRuns = useCallback(async () => {
    try {
      setRuns((await listEvaluations()).items);
    } catch (caught) {
      setError(describeError(caught));
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  // Còn lượt đang chạy thì cập nhật định kỳ để thấy tiến độ.
  const hasUnfinished = runs.some((run) => UNFINISHED.has(run.status));
  useEffect(() => {
    if (!hasUnfinished) return undefined;
    const timer = setInterval(loadRuns, POLL_MS);
    return () => clearInterval(timer);
  }, [hasUnfinished, loadRuns]);

  async function handleCreated(run) {
    await loadRuns();
    setSelectedId(run.id);
  }

  const selected = runs.find((run) => run.id === selectedId) ?? null;

  return (
    <section className="evaluations-layout">
      <div className="evaluations-side">
        <NewEvaluationForm onCreated={handleCreated} onError={setError} />
        <h2>Các lượt đánh giá</h2>
        {runs.length === 0 ? (
          <p className="muted">Chưa có lượt đánh giá nào.</p>
        ) : (
          <ul className="plain-list">
            {runs.map((run) => (
              <li key={run.id}>
                <button
                  type="button"
                  className={`list-button run-list-item${run.id === selectedId ? " active" : ""}`}
                  onClick={() => setSelectedId(run.id)}
                >
                  <span>{formatDateTime(run.created_at)}</span>
                  <span className={`badge badge--run-${run.status}`}>{RUN_STATUS_LABELS[run.status]}</span>
                  <span className="muted">
                    {run.environment?.model_configuration?.llm_model ?? "?"} · {run.completed_cases + run.failed_cases}/{run.total_cases} câu
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="evaluations-main">
        {error && (
          <div className="alert alert--error" role="alert">
            {error}
          </div>
        )}
        {selected ? <RunDetail run={selected} onError={setError} /> : <p className="empty-state">Chọn một lượt đánh giá để xem kết quả.</p>}
      </div>
    </section>
  );
}

function NewEvaluationForm({ onCreated, onError }) {
  const [versions, setVersions] = useState([]);
  const [configs, setConfigs] = useState([]);
  const [capabilities, setCapabilities] = useState(null);
  const [form, setForm] = useState({ datasetVersionId: "", modelConfigurationId: "", judgeModel: "" });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // Chỉ phiên bản đã duyệt mới đánh giá được (để kết quả tái lập được).
    listDatasets()
      .then(async ({ items }) => {
        const all = await Promise.all(
          items.map(async (dataset) =>
            (await listVersions(dataset.id)).items
              .filter((version) => version.status === "reviewed")
              .map((version) => ({ ...version, datasetName: dataset.name })),
          ),
        );
        setVersions(all.flat());
      })
      .catch((caught) => onError(describeError(caught)));
    listConfigurations()
      .then((result) => setConfigs(result.items))
      .catch(() => setConfigs([]));
    getCapabilities()
      .then(setCapabilities)
      .catch(() => setCapabilities(null));
  }, [onError]);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    onError(null);
    try {
      onCreated(await createEvaluation(form));
    } catch (caught) {
      onError(describeError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  return (
    <form className="card evaluation-form" onSubmit={handleSubmit}>
      <h2>Tạo lượt đánh giá</h2>
      <label>
        Phiên bản dataset (đã duyệt)
        <select value={form.datasetVersionId} onChange={update("datasetVersionId")} required>
          <option value="">— chọn —</option>
          {versions.map((version) => (
            <option key={version.id} value={version.id}>
              {version.datasetName} · v{version.version_number} ({version.test_case_count} câu)
            </option>
          ))}
        </select>
      </label>
      {versions.length === 0 && <p className="hint">Chưa có phiên bản nào được duyệt. Vào trang Dataset để duyệt trước.</p>}
      <label>
        Cấu hình mô hình
        <select value={form.modelConfigurationId} onChange={update("modelConfigurationId")}>
          <option value="">Mặc định của máy chủ</option>
          {configs.map((config) => (
            <option key={config.id} value={config.id}>
              {config.name} ({config.llm_model}, top_k={config.top_k})
            </option>
          ))}
        </select>
      </label>
      {capabilities?.llm_configured ? (
        <label>
          Judge model (để trống nếu không chấm faithfulness/relevancy)
          <input value={form.judgeModel} onChange={update("judgeModel")} maxLength={100} placeholder="ví dụ: tên model của provider" />
        </label>
      ) : (
        <p className="hint">Máy chủ chưa cấu hình LLM: chỉ chấm metric truy xuất và hành vi, không có LLM judge.</p>
      )}
      <button type="submit" className="button button--primary" disabled={submitting || !form.datasetVersionId}>
        {submitting ? "Đang tạo…" : "Chạy đánh giá"}
      </button>
    </form>
  );
}

function RunDetail({ run, onError }) {
  const [results, setResults] = useState({ items: [], total: 0 });
  const [filters, setFilters] = useState({ status: "", category: "" });
  const [details, setDetails] = useState(null);
  const config = run.environment?.model_configuration ?? {};
  const dataset = run.environment?.dataset_version ?? {};
  const progress = run.completed_cases + run.failed_cases;

  useEffect(() => {
    let cancelled = false;
    listResults(run.id, filters)
      .then((result) => !cancelled && setResults(result))
      .catch((caught) => !cancelled && onError(describeError(caught)));
    return () => {
      cancelled = true;
    };
    // Tải lại khi tiến độ thay đổi để thấy câu mới xong.
  }, [run.id, progress, filters, onError]);

  useEffect(() => {
    getEvaluation(run.id)
      .then(setDetails)
      .catch(() => setDetails(null));
  }, [run.id, run.status]);

  async function handleDownload() {
    try {
      const blob = await downloadReport(run.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `evaluation-${run.id}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      onError(describeError(caught));
    }
  }

  const aggregates = (details ?? run).aggregate_metrics;
  const categories = Object.entries(run.categories ?? {});
  const warnings = run.environment?.warnings ?? [];

  return (
    <article className="run-detail">
      <header className="toolbar">
        <div>
          <h2>
            Lượt đánh giá <span className={`badge badge--run-${run.status}`}>{RUN_STATUS_LABELS[run.status]}</span>
          </h2>
          <p className="muted">
            Dataset v{dataset.version_number ?? "?"} · {config.llm_provider}/{config.llm_model} · top_k={config.top_k} · prompt{" "}
            {config.prompt_version} · chunk {config.chunk_size}/{config.chunk_overlap} · judge: {run.judge_model ?? "không dùng"}
          </p>
        </div>
        <button type="button" className="button button--ghost" onClick={handleDownload} disabled={run.status !== "completed"}>
          Tải báo cáo CSV
        </button>
      </header>

      {UNFINISHED.has(run.status) && (
        <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={run.total_cases} aria-valuenow={progress}>
          <span className="progress__fill" style={{ width: `${run.total_cases ? (progress / run.total_cases) * 100 : 0}%` }} />
          <span className="progress__label">
            {progress}/{run.total_cases} câu
          </span>
        </div>
      )}
      {run.error_message && <p className="alert alert--error">{run.error_message}</p>}
      {warnings.map((warning) => (
        <p key={warning} className="notice">
          {warning}
        </p>
      ))}

      <div className="run-summary">
        <section className="card">
          <h3>Metric trung bình</h3>
          <MetricBars metrics={aggregates} />
        </section>
        <section className="card">
          <h3>Phân loại lỗi</h3>
          {categories.length === 0 ? (
            <p className="muted">Chưa có.</p>
          ) : (
            <ul className="category-list">
              {categories.map(([category, count]) => (
                <li key={category}>
                  <button
                    type="button"
                    className={`link-button${filters.category === category ? " active" : ""}`}
                    onClick={() => setFilters((current) => ({ ...current, category: current.category === category ? "" : category }))}
                  >
                    {CATEGORY_LABELS[category] ?? category}
                  </button>
                  <span>{count}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="hint">Số liệu từ bộ câu hỏi này; chưa có baseline nên không đặt ngưỡng đạt/không đạt.</p>
        </section>
      </div>

      <div className="toolbar">
        <h3>Kết quả từng câu ({results.total})</h3>
        <div className="form-actions">
          <label className="chat-config">
            Trạng thái
            <select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}>
              <option value="">Tất cả</option>
              <option value="ok">Chạy được</option>
              <option value="error">Lỗi</option>
            </select>
          </label>
          <label className="chat-config">
            Phân loại
            <select value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}>
              <option value="">Tất cả</option>
              {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <ol className="result-list">
        {results.items.map((result) => (
          <ResultItem key={result.id} result={result} />
        ))}
      </ol>
    </article>
  );
}

function ResultItem({ result }) {
  return (
    <li className={`result-item result-item--${result.category}`}>
      <div className="result-item__head">
        <strong className="prose-wrap">{result.question}</strong>
        <span className="badge">{CATEGORY_LABELS[result.category] ?? result.category}</span>
      </div>
      <p className="muted">
        Kỳ vọng: {result.expected_behavior === "answer" ? "trả lời" : "từ chối (không đủ thông tin)"} · {formatLatency(result.latency_ms)} · chi
        phí {formatCost(result.estimated_cost)}
      </p>
      {result.error_message && <p className="cell-error">{result.error_message}</p>}
      <details>
        <summary>Chi tiết: câu trả lời, metric, đoạn lấy về</summary>
        <div className="result-item__body">
          <h4>Câu trả lời của hệ thống</h4>
          <p className="prose-wrap">{result.answer ?? "—"}</p>
          {result.ground_truth_answer && (
            <>
              <h4>Đáp án tham chiếu</h4>
              <p className="prose-wrap">{result.ground_truth_answer}</p>
            </>
          )}
          <h4>Metric</h4>
          <ul className="metric-inline">
            {result.metrics.map((metric) => (
              <li key={`${metric.metric_name}-${metric.k ?? ""}`}>
                {metricName(metric)}:{" "}
                {metric.status === "computed" ? formatScore(metric.value) : METRIC_STATUS_LABELS[metric.status] ?? metric.status}
                {metric.details?.reason && <span className="muted"> ({metric.details.reason})</span>}
              </li>
            ))}
          </ul>
          <h4>Đoạn lấy về</h4>
          {result.contexts.length === 0 ? (
            <p className="muted">Không có.</p>
          ) : (
            <ol className="context-list">
              {result.contexts.map((context) => (
                <li key={context.rank}>
                  <span className="muted">
                    #{context.rank} · {context.filename}
                    {context.page_number ? ` · trang ${context.page_number}` : ""} · điểm {context.score}
                    {context.relevant === true && " · đúng"}
                    {context.relevant === false && " · không khớp tham chiếu"}
                  </span>
                  <blockquote className="prose-wrap">{context.snippet}</blockquote>
                </li>
              ))}
            </ol>
          )}
        </div>
      </details>
    </li>
  );
}
