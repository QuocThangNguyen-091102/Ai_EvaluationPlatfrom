import { useCallback, useEffect, useState } from "react";

import RunProgress from "../components/RunProgress.jsx";
import { describeError, formatDateTime, formatLatency } from "../formatting.js";
import { RUN_STATUS_LABELS } from "../metricLabels.js";
import { getCapabilities, listConfigurations } from "../services/api/modelConfigApi.js";
import {
  createSecurityRun,
  downloadSecurityReport,
  listSecurityResults,
  listSecurityRuns,
  listSecurityTestCases,
} from "../services/api/securityApi.js";

const POLL_MS = 2000;
const UNFINISHED = new Set(["pending", "running"]);

const SECURITY_CATEGORY_LABELS = {
  prompt_injection: "Prompt injection",
  jailbreak: "Jailbreak",
  data_leakage: "Rò rỉ dữ liệu",
  access_control: "Kiểm soát truy cập",
  malicious_documents: "Tài liệu độc",
};
const RESULT_LABELS = { pass: "Đạt", fail: "Không đạt", error: "Lỗi", skipped: "Bỏ qua" };
const SEVERITY_LABELS = { critical: "Nghiêm trọng", high: "Cao", medium: "Trung bình", low: "Thấp" };
const EVALUATOR_LABELS = { rule: "luật", judge: "judge", none: "—" };

export default function SecurityPage() {
  const [runs, setRuns] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);

  const loadRuns = useCallback(async () => {
    try {
      setRuns((await listSecurityRuns()).items);
    } catch (caught) {
      setError(describeError(caught));
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

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
        <NewSecurityRunForm onCreated={handleCreated} onError={setError} />
        <h2>Các lượt kiểm thử</h2>
        {runs.length === 0 ? (
          <p className="muted">Chưa có lượt kiểm thử nào.</p>
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
                    {run.environment?.model_configuration?.llm_model ?? "?"} · {run.completed_cases}/{run.total_cases} test
                    {run.summary?.by_status?.fail ? ` · ${run.summary.by_status.fail} không đạt` : ""}
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
        {selected ? (
          <SecurityRunDetail run={selected} onError={setError} />
        ) : (
          <div className="card">
            <h2>Kiểm thử bảo mật</h2>
            <p>
              Mỗi lượt chạy bộ test trong một <strong>sandbox riêng</strong>: hệ thống tạo tài liệu thử và hai tài khoản tạm (kẻ tấn công, nạn
              nhân), gửi câu hỏi qua đúng RAG pipeline của trang Hỏi đáp, rồi xóa sandbox. Tài liệu của bạn không bị dùng hay thay đổi.
            </p>
            <p className="hint">Kết quả cho biết bộ test này pass hay fail, không chứng minh hệ thống an toàn tuyệt đối. Xem phần giới hạn trong mỗi lượt.</p>
          </div>
        )}
      </div>
    </section>
  );
}

function NewSecurityRunForm({ onCreated, onError }) {
  const [catalog, setCatalog] = useState([]);
  const [configs, setConfigs] = useState([]);
  const [capabilities, setCapabilities] = useState(null);
  const [categories, setCategories] = useState([]);
  const [modelConfigurationId, setModelConfigurationId] = useState("");
  const [judgeModel, setJudgeModel] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listSecurityTestCases()
      .then((result) => setCatalog(result.items))
      .catch((caught) => onError(describeError(caught)));
    listConfigurations()
      .then((result) => setConfigs(result.items))
      .catch(() => setConfigs([]));
    getCapabilities()
      .then(setCapabilities)
      .catch(() => setCapabilities(null));
  }, [onError]);

  function toggle(category) {
    setCategories((current) => (current.includes(category) ? current.filter((c) => c !== category) : [...current, category]));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    onError(null);
    try {
      onCreated(await createSecurityRun({ modelConfigurationId, categories, judgeModel }));
    } catch (caught) {
      onError(describeError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  const counts = catalog.reduce((acc, item) => ({ ...acc, [item.category]: (acc[item.category] ?? 0) + 1 }), {});

  return (
    <form className="card evaluation-form" onSubmit={handleSubmit}>
      <h2>Tạo lượt kiểm thử</h2>
      <fieldset className="category-picker">
        <legend>Nhóm test (không chọn = cả 5 nhóm)</legend>
        {Object.entries(SECURITY_CATEGORY_LABELS).map(([value, label]) => (
          <label key={value} className="checkbox">
            <input type="checkbox" checked={categories.includes(value)} onChange={() => toggle(value)} />
            {label} <span className="muted">({counts[value] ?? 0})</span>
          </label>
        ))}
      </fieldset>
      <label>
        Cấu hình mô hình
        <select value={modelConfigurationId} onChange={(event) => setModelConfigurationId(event.target.value)}>
          <option value="">Mặc định của máy chủ</option>
          {configs.map((config) => (
            <option key={config.id} value={config.id}>
              {config.name} ({config.llm_model})
            </option>
          ))}
        </select>
      </label>
      {capabilities?.llm_configured ? (
        <label>
          Judge model (tùy chọn, phát hiện lộ thông tin dạng diễn giải)
          <input value={judgeModel} onChange={(event) => setJudgeModel(event.target.value)} maxLength={100} />
        </label>
      ) : (
        <p className="hint">Máy chủ chưa cấu hình LLM: chỉ các test kiểm soát truy cập và secret chạy thật; test cần LLM sẽ được đánh dấu bỏ qua.</p>
      )}
      <button type="submit" className="button button--primary" disabled={submitting}>
        {submitting ? "Đang tạo…" : "Chạy kiểm thử"}
      </button>
    </form>
  );
}

function SecurityRunDetail({ run, onError }) {
  const [results, setResults] = useState({ items: [], total: 0 });
  const [filters, setFilters] = useState({ status: "", severity: "", category: "" });
  const byStatus = run.summary?.by_status ?? {};
  const failedBySeverity = run.summary?.failed_by_severity ?? {};
  const config = run.environment?.model_configuration ?? {};

  useEffect(() => {
    let cancelled = false;
    listSecurityResults(run.id, filters)
      .then((result) => !cancelled && setResults(result))
      .catch((caught) => !cancelled && onError(describeError(caught)));
    return () => {
      cancelled = true;
    };
  }, [run.id, run.completed_cases, filters, onError]);

  async function handleDownload() {
    try {
      const blob = await downloadSecurityReport(run.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `security-${run.id}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      onError(describeError(caught));
    }
  }

  const setFilter = (field) => (event) => setFilters((current) => ({ ...current, [field]: event.target.value }));

  return (
    <article className="run-detail">
      <header className="toolbar">
        <div>
          <h2>
            Lượt kiểm thử <span className={`badge badge--run-${run.status}`}>{RUN_STATUS_LABELS[run.status]}</span>
          </h2>
          <p className="muted">
            {config.llm_provider}/{config.llm_model} · prompt {config.prompt_version} · top_k={config.top_k} · judge: {run.judge_model ?? "không dùng"} ·
            nhóm: {run.categories.length ? run.categories.map((c) => SECURITY_CATEGORY_LABELS[c]).join(", ") : "cả 5 nhóm"}
          </p>
        </div>
        <button type="button" className="button button--ghost" onClick={handleDownload} disabled={run.status !== "completed"}>
          Tải báo cáo CSV
        </button>
      </header>

      <RunProgress
        key={run.id}
        status={run.status}
        completed={run.completed_cases}
        total={run.total_cases}
        unit="test"
        createdAt={run.created_at}
        startedAt={run.started_at}
        finishedAt={run.finished_at}
      />
      {run.error_message && <p className="alert alert--error">{run.error_message}</p>}

      <div className="run-summary">
        <section className="card">
          <h3>Kết quả</h3>
          <ul className="stat-list">
            {Object.entries(RESULT_LABELS).map(([status, label]) => (
              <li key={status} className={`stat stat--${status}`}>
                <span className="stat__value">{byStatus[status] ?? 0}</span>
                <span className="stat__label">{label}</span>
              </li>
            ))}
          </ul>
          {Object.keys(failedBySeverity).length > 0 && (
            <p>
              Không đạt theo mức độ:{" "}
              {Object.entries(SEVERITY_LABELS)
                .filter(([severity]) => failedBySeverity[severity])
                .map(([severity, label]) => `${label}: ${failedBySeverity[severity]}`)
                .join(" · ")}
            </p>
          )}
        </section>
        <section className="card">
          <h3>Giới hạn của lượt này</h3>
          <ul className="coverage-notes">
            {run.coverage_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      </div>

      <div className="toolbar">
        <h3>Từng test ({results.total})</h3>
        <div className="form-actions">
          <label className="chat-config">
            Kết quả
            <select value={filters.status} onChange={setFilter("status")}>
              <option value="">Tất cả</option>
              {Object.entries(RESULT_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="chat-config">
            Mức độ
            <select value={filters.severity} onChange={setFilter("severity")}>
              <option value="">Tất cả</option>
              {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="chat-config">
            Nhóm
            <select value={filters.category} onChange={setFilter("category")}>
              <option value="">Tất cả</option>
              {Object.entries(SECURITY_CATEGORY_LABELS).map(([value, label]) => (
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
          <SecurityResultItem key={result.id} result={result} />
        ))}
      </ol>
    </article>
  );
}

function SecurityResultItem({ result }) {
  const violations = result.evidence?.violations ?? [];
  const judge = result.evidence?.judge;
  return (
    <li className={`result-item security-result--${result.status}`}>
      <div className="result-item__head">
        <strong className="prose-wrap">
          {result.case_key} · {result.title}
        </strong>
        <span className={`badge badge--security-${result.status}`}>{RESULT_LABELS[result.status]}</span>
      </div>
      <p className="muted">
        {SECURITY_CATEGORY_LABELS[result.category]} · mức {SEVERITY_LABELS[result.severity]} · chấm bằng {EVALUATOR_LABELS[result.evaluator]} ·{" "}
        {formatLatency(result.latency_ms)}
      </p>
      {violations.length > 0 && (
        <ul className="violations">
          {violations.map((violation) => (
            <li key={violation.rule + violation.detail}>{violation.detail}</li>
          ))}
        </ul>
      )}
      {result.evidence?.reason && <p className="muted">{result.evidence.reason}</p>}
      {result.error_message && <p className="cell-error">{result.error_message}</p>}
      <details>
        <summary>Chi tiết: mô tả, câu trả lời, đoạn lấy về, cách giảm thiểu</summary>
        <div className="result-item__body">
          <p className="prose-wrap">{result.description}</p>
          <h4>Hành vi mong đợi</h4>
          <p className="prose-wrap">{result.expected_behavior}</p>
          <h4>Câu trả lời thực tế</h4>
          <p className="prose-wrap">{result.actual_response ?? "—"}</p>
          {judge && (
            <>
              <h4>Judge</h4>
              <p className="prose-wrap">
                {judge.status === "computed" ? (judge.violated ? "Vi phạm" : "Không vi phạm") : judge.status}
                {judge.reason ? `: ${judge.reason}` : ""}
              </p>
            </>
          )}
          <h4>Đoạn lấy về ({result.contexts.length})</h4>
          {result.contexts.length > 0 && (
            <ol className="context-list">
              {result.contexts.map((context) => (
                <li key={context.rank}>
                  <span className="muted">
                    #{context.rank} · {context.filename} · điểm {context.score}
                  </span>
                  <blockquote className="prose-wrap">{context.snippet}</blockquote>
                </li>
              ))}
            </ol>
          )}
          <h4>Cách giảm thiểu</h4>
          <p className="prose-wrap">{result.mitigation}</p>
        </div>
      </details>
    </li>
  );
}
