import { useCallback, useEffect, useState } from "react";

import { describeError, formatCost, formatDateTime, formatLatency } from "../formatting.js";
import { METRIC_LABELS, METRIC_STATUS_LABELS, RUN_STATUS_LABELS, formatScore } from "../metricLabels.js";
import { createBenchmark, downloadBenchmarkReport, listBenchmarks } from "../services/api/benchmarkApi.js";
import { listDatasets, listVersions } from "../services/api/datasetApi.js";
import { createConfiguration, getCapabilities, listConfigurations } from "../services/api/modelConfigApi.js";

const POLL_MS = 2000;
const UNFINISHED = new Set(["pending", "running"]);
const VARIABLES = {
  top_k: { label: "top_k (số đoạn lấy về)", placeholder: "ví dụ: 3, 5, 8" },
  llm_model: { label: "LLM model", placeholder: "tên các model, cách nhau bằng dấu phẩy" },
  prompt_version: { label: "Prompt version", placeholder: "ví dụ: rag-v1" },
};
const COLUMNS = [
  "behavior_correct",
  "recall_at_k",
  "mrr",
  "ndcg_at_k",
  "precision_at_k",
  "context_precision",
  "context_recall",
  "faithfulness",
  "answer_relevancy",
];

export default function BenchmarksPage() {
  const [benchmarks, setBenchmarks] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setBenchmarks((await listBenchmarks()).items);
    } catch (caught) {
      setError(describeError(caught));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const hasUnfinished = benchmarks.some((b) => UNFINISHED.has(b.status));
  useEffect(() => {
    if (!hasUnfinished) return undefined;
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [hasUnfinished, load]);

  async function handleCreated(benchmark) {
    await load();
    setSelectedId(benchmark.id);
  }

  const selected = benchmarks.find((b) => b.id === selectedId) ?? null;

  return (
    <section className="evaluations-layout">
      <div className="evaluations-side">
        <NewBenchmarkForm onCreated={handleCreated} onError={setError} />
        <h2>Các benchmark</h2>
        {benchmarks.length === 0 ? (
          <p className="muted">Chưa có benchmark nào.</p>
        ) : (
          <ul className="plain-list">
            {benchmarks.map((benchmark) => (
              <li key={benchmark.id}>
                <button
                  type="button"
                  className={`list-button run-list-item${benchmark.id === selectedId ? " active" : ""}`}
                  onClick={() => setSelectedId(benchmark.id)}
                >
                  <span>{benchmark.name}</span>
                  <span className={`badge badge--run-${benchmark.status}`}>{RUN_STATUS_LABELS[benchmark.status]}</span>
                  <span className="muted">
                    {formatDateTime(benchmark.created_at)} · {benchmark.variants.length} cấu hình · đổi {benchmark.varied_variable}
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
          <BenchmarkDetail benchmark={selected} onError={setError} />
        ) : (
          <div className="card">
            <h2>Benchmark</h2>
            <p>
              So sánh nhiều cấu hình trên <strong>cùng một phiên bản dataset</strong>, mỗi lần chỉ đổi <strong>một biến</strong> (top_k, LLM model
              hoặc prompt). Mỗi cấu hình là một lượt đánh giá bình thường, xem chi tiết ở trang Đánh giá.
            </p>
            <p className="hint">Khác biệt nhỏ trên bộ câu hỏi nhỏ có thể chỉ là ngẫu nhiên; chưa có kiểm định thống kê.</p>
          </div>
        )}
      </div>
    </section>
  );
}

function NewBenchmarkForm({ onCreated, onError }) {
  const [versions, setVersions] = useState([]);
  const [configs, setConfigs] = useState([]);
  const [capabilities, setCapabilities] = useState(null);
  const [form, setForm] = useState({ name: "", datasetVersionId: "", baseConfigId: "", variedVariable: "top_k", values: "", judgeModel: "" });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
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

  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  async function handleSubmit(event) {
    event.preventDefault();
    const base = configs.find((config) => config.id === form.baseConfigId);
    const values = [...new Set(form.values.split(",").map((v) => v.trim()).filter(Boolean))];
    if (!base) return onError("Chọn cấu hình gốc");
    if (values.length < 2) return onError("Cần ít nhất 2 giá trị khác nhau để so sánh");
    setSubmitting(true);
    onError(null);
    try {
      // Mỗi giá trị là một cấu hình mới: chép cấu hình gốc, chỉ đổi đúng biến được chọn.
      const ids = [];
      for (const value of values) {
        const variant = form.variedVariable === "top_k" ? Number(value) : value;
        const created = await createConfiguration({
          name: `${form.name.trim()} · ${form.variedVariable}=${value}`.slice(0, 100),
          llm_provider: base.llm_provider,
          llm_model: base.llm_model,
          prompt_version: base.prompt_version,
          top_k: base.top_k,
          temperature: base.temperature,
          chunk_size: base.chunk_size,
          chunk_overlap: base.chunk_overlap,
          [form.variedVariable]: variant,
        });
        ids.push(created.id);
      }
      onCreated(
        await createBenchmark({
          name: form.name.trim(),
          datasetVersionId: form.datasetVersionId,
          variedVariable: form.variedVariable,
          modelConfigurationIds: ids,
          judgeModel: form.judgeModel,
        }),
      );
    } catch (caught) {
      onError(describeError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card evaluation-form" onSubmit={handleSubmit}>
      <h2>Tạo benchmark</h2>
      <label>
        Tên benchmark
        <input value={form.name} onChange={update("name")} maxLength={60} required />
      </label>
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
      <label>
        Cấu hình gốc
        <select value={form.baseConfigId} onChange={update("baseConfigId")} required>
          <option value="">— chọn —</option>
          {configs.map((config) => (
            <option key={config.id} value={config.id}>
              {config.name}
            </option>
          ))}
        </select>
      </label>
      {configs.length === 0 && <p className="hint">Chưa có cấu hình nào. Hỏi một câu ở trang Hỏi đáp để tạo cấu hình mặc định.</p>}
      <label>
        Biến thay đổi
        <select value={form.variedVariable} onChange={update("variedVariable")}>
          {Object.entries(VARIABLES).map(([value, { label }]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Các giá trị
        <input value={form.values} onChange={update("values")} placeholder={VARIABLES[form.variedVariable].placeholder} required />
      </label>
      {capabilities?.llm_configured ? (
        <label>
          Judge model (tùy chọn)
          <input value={form.judgeModel} onChange={update("judgeModel")} maxLength={100} />
        </label>
      ) : (
        <p className="hint">Máy chủ chưa cấu hình LLM: chỉ so sánh được top_k ở chế độ trích đoạn.</p>
      )}
      <button type="submit" className="button button--primary" disabled={submitting}>
        {submitting ? "Đang tạo…" : "Chạy benchmark"}
      </button>
    </form>
  );
}

function BenchmarkDetail({ benchmark, onError }) {
  async function handleDownload() {
    try {
      const blob = await downloadBenchmarkReport(benchmark.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `benchmark-${benchmark.id}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      onError(describeError(caught));
    }
  }

  const done = benchmark.variants.filter((v) => !UNFINISHED.has(v.status)).length;

  return (
    <article className="run-detail">
      <header className="toolbar">
        <div>
          <h2>
            {benchmark.name} <span className={`badge badge--run-${benchmark.status}`}>{RUN_STATUS_LABELS[benchmark.status]}</span>
          </h2>
          <p className="muted">
            Đổi biến: {benchmark.varied_variable} · {benchmark.variants.length} cấu hình · judge: {benchmark.judge_model ?? "không dùng"}
          </p>
        </div>
        <button type="button" className="button button--ghost" onClick={handleDownload} disabled={benchmark.status !== "completed"}>
          Tải báo cáo CSV
        </button>
      </header>
      {UNFINISHED.has(benchmark.status) && (
        <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={benchmark.variants.length} aria-valuenow={done}>
          <span className="progress__fill" style={{ width: `${(done / benchmark.variants.length) * 100}%` }} />
          <span className="progress__label">
            {done}/{benchmark.variants.length} cấu hình
          </span>
        </div>
      )}
      {benchmark.error_message && <p className="alert alert--error">{benchmark.error_message}</p>}
      {benchmark.notes.map((note) => (
        <p key={note} className="notice">
          {note}
        </p>
      ))}

      <section className="card">
        <h3>Chất lượng</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{benchmark.varied_variable}</th>
                {COLUMNS.map((name) => (
                  <th key={name} title={METRIC_LABELS[name]?.hint}>
                    {METRIC_LABELS[name]?.label ?? name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {benchmark.variants.map((variant) => {
                const byName = Object.fromEntries(variant.aggregate_metrics.map((m) => [m.metric_name, m]));
                return (
                  <tr key={variant.evaluation_run_id}>
                    <th scope="row">{String(variant.varied_value)}</th>
                    {COLUMNS.map((name) => {
                      const metric = byName[name];
                      if (!metric) return <td key={name}>—</td>;
                      if (metric.status !== "computed")
                        return (
                          <td key={name} className="muted">
                            {METRIC_STATUS_LABELS[metric.status] ?? metric.status}
                          </td>
                        );
                      return (
                        <td key={name}>
                          <span className="score-cell">
                            <span className="score-cell__bar" style={{ width: `${Math.max(0, Math.min(1, metric.value)) * 100}%` }} aria-hidden="true" />
                            <span className="score-cell__value">{formatScore(metric.value)}</span>
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h3>Độ trễ, token, chi phí</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{benchmark.varied_variable}</th>
                <th>Trạng thái</th>
                <th>Câu (lỗi)</th>
                <th>Trung bình</th>
                <th>p50</th>
                <th>p95</th>
                <th>Token vào / ra</th>
                <th>Chi phí ước tính</th>
              </tr>
            </thead>
            <tbody>
              {benchmark.variants.map((variant) => {
                const usage = variant.usage;
                return (
                  <tr key={variant.evaluation_run_id}>
                    <th scope="row">{String(variant.varied_value)}</th>
                    <td>{RUN_STATUS_LABELS[variant.status]}</td>
                    <td>
                      {variant.total_cases} ({variant.failed_cases})
                    </td>
                    <td>{formatLatency(usage.latency_mean_ms == null ? null : Math.round(usage.latency_mean_ms))}</td>
                    <td>{formatLatency(usage.latency_p50_ms)}</td>
                    <td>{formatLatency(usage.latency_p95_ms)}</td>
                    <td>
                      {usage.prompt_tokens ?? "không rõ"} / {usage.completion_tokens ?? "không rõ"}
                    </td>
                    <td>
                      {formatCost(usage.total_cost)}
                      {usage.cost_incomplete && <span className="muted"> (thiếu giá một phần)</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="hint">Độ trễ đo trên máy chủ hiện tại, gồm embed câu hỏi, truy xuất và sinh câu trả lời. p95 với ít câu hỏi chỉ là giá trị lớn nhất gần đúng.</p>
      </section>
    </article>
  );
}
