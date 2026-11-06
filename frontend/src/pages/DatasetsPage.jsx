import { useCallback, useEffect, useRef, useState } from "react";

import TestCaseForm, { DIFFICULTY_LABELS, QUESTION_TYPE_LABELS } from "../components/TestCaseForm.jsx";
import { describeError } from "../formatting.js";
import {
  addTestCase,
  createDataset,
  createVersion,
  deleteTestCase,
  importTestCases,
  listDatasets,
  listTestCases,
  listVersions,
  reviewVersion,
  updateTestCase,
} from "../services/api/datasetApi.js";
import { listDocuments } from "../services/api/documentApi.js";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState([]);
  const [datasetId, setDatasetId] = useState(null);
  const [versions, setVersions] = useState([]);
  const [versionId, setVersionId] = useState(null);
  const [cases, setCases] = useState({ items: [], total: 0 });
  const [filters, setFilters] = useState({ questionType: "", difficulty: "" });
  const [documents, setDocuments] = useState([]);
  const [newName, setNewName] = useState("");
  const [editing, setEditing] = useState(null); // null | "new" | test case
  const [error, setError] = useState(null);
  const [importErrors, setImportErrors] = useState([]);
  const [message, setMessage] = useState(null);
  const importInput = useRef(null);

  const version = versions.find((v) => v.id === versionId) ?? null;
  const frozen = version?.status === "reviewed";

  const run = useCallback(async (action) => {
    setError(null);
    try {
      return await action();
    } catch (caught) {
      setError(describeError(caught));
      return undefined;
    }
  }, []);

  const loadDatasets = useCallback(() => run(async () => setDatasets((await listDatasets()).items)), [run]);

  useEffect(() => {
    loadDatasets();
    listDocuments({ limit: 100, status: "ready" })
      .then((result) => setDocuments(result.items))
      .catch(() => setDocuments([]));
  }, [loadDatasets]);

  const loadVersions = useCallback(
    async (id, preferredVersionId) => {
      const result = await run(() => listVersions(id));
      if (!result) return;
      setVersions(result.items);
      setVersionId(preferredVersionId ?? result.items[0]?.id ?? null);
    },
    [run],
  );

  const loadCases = useCallback(async () => {
    if (!versionId) return;
    const result = await run(() => listTestCases(versionId, filters));
    if (result) setCases(result);
  }, [versionId, filters, run]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  async function selectDataset(id) {
    setDatasetId(id);
    setEditing(null);
    setMessage(null);
    await loadVersions(id);
  }

  async function handleCreateDataset(event) {
    event.preventDefault();
    const created = await run(() => createDataset(newName.trim()));
    if (!created) return;
    setNewName("");
    await loadDatasets();
    await selectDataset(created.id);
  }

  async function handleNewVersion() {
    const created = await run(() => createVersion(datasetId, versionId));
    if (created) {
      setMessage(`Đã tạo phiên bản ${created.version_number} (sao chép ${created.test_case_count} câu).`);
      await loadVersions(datasetId, created.id);
    }
  }

  async function handleReview() {
    if (!window.confirm("Duyệt và đóng băng phiên bản này? Sau khi duyệt sẽ không sửa được, chỉ tạo được phiên bản mới.")) return;
    const reviewed = await run(() => reviewVersion(versionId));
    if (reviewed) {
      setMessage(`Phiên bản ${reviewed.version_number} đã được duyệt với ${reviewed.test_case_count} câu.`);
      await loadVersions(datasetId, versionId);
    }
  }

  async function handleSave(payload) {
    // Lỗi ném ra để form hiện ngay dưới các ô nhập.
    if (editing === "new") {
      await addTestCase(versionId, payload);
    } else {
      await updateTestCase(editing.id, payload);
    }
    setEditing(null);
    await loadCases();
    await loadVersions(datasetId, versionId);
  }

  async function handleDelete(testCase) {
    if (!window.confirm("Xóa câu hỏi này?")) return;
    const done = await run(async () => {
      await deleteTestCase(testCase.id);
      return true;
    });
    if (done) {
      await loadCases();
      await loadVersions(datasetId, versionId);
    }
  }

  async function handleImport(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setImportErrors([]);
    setMessage(null);
    setError(null);
    try {
      const result = await importTestCases(versionId, file);
      setMessage(`Đã nhập ${result.imported} câu hỏi.`);
      await loadCases();
      await loadVersions(datasetId, versionId);
    } catch (caught) {
      setError(describeErrorShort(caught));
      setImportErrors(Array.isArray(caught.details) ? caught.details.filter((d) => d.row) : []);
    } finally {
      if (importInput.current) importInput.current.value = "";
    }
  }

  return (
    <section className="datasets-layout">
      <aside className="datasets-sidebar" aria-label="Danh sách dataset">
        <h1>Dataset</h1>
        <form className="inline-form" onSubmit={handleCreateDataset}>
          <label className="visually-hidden" htmlFor="new-dataset">
            Tên dataset mới
          </label>
          <input id="new-dataset" type="text" placeholder="Tên dataset mới" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <button type="submit" className="button button--primary button--small" disabled={!newName.trim()}>
            Tạo
          </button>
        </form>
        <ul className="plain-list">
          {datasets.map((dataset) => (
            <li key={dataset.id}>
              <button type="button" className={`list-button${dataset.id === datasetId ? " active" : ""}`} onClick={() => selectDataset(dataset.id)}>
                {dataset.name}
              </button>
            </li>
          ))}
        </ul>
        {datasets.length === 0 && <p className="muted">Chưa có dataset nào.</p>}
      </aside>

      <div className="datasets-main">
        {error && (
          <div className="alert alert--error" role="alert">
            {error}
            {importErrors.length > 0 && (
              <ul className="import-errors">
                {importErrors.map((item, index) => (
                  <li key={index}>
                    Dòng {item.row}: {item.issue}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {message && (
          <p className="notice" role="status">
            {message}
          </p>
        )}

        {!datasetId ? (
          <p className="empty-state">Chọn hoặc tạo một dataset để quản lý câu hỏi đánh giá.</p>
        ) : (
          <>
            <div className="toolbar">
              <label className="chat-config">
                Phiên bản
                <select value={versionId ?? ""} onChange={(e) => setVersionId(e.target.value)}>
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      Phiên bản {v.version_number} · {v.status === "reviewed" ? "đã duyệt" : "nháp"} · {v.test_case_count} câu
                    </option>
                  ))}
                </select>
              </label>
              <div className="form-actions">
                <button type="button" className="button button--ghost" onClick={handleNewVersion}>
                  Tạo phiên bản mới từ bản này
                </button>
                {!frozen && (
                  <button type="button" className="button button--primary" onClick={handleReview} disabled={!version?.test_case_count}>
                    Duyệt và đóng băng
                  </button>
                )}
              </div>
            </div>

            {frozen && <p className="notice">Phiên bản đã duyệt: chỉ xem, không sửa. Tạo phiên bản mới nếu cần thay đổi.</p>}

            {!frozen && !editing && (
              <div className="form-actions">
                <button type="button" className="button button--primary" onClick={() => setEditing("new")}>
                  Thêm câu hỏi
                </button>
                <button type="button" className="button button--ghost" onClick={() => importInput.current?.click()}>
                  Nhập từ file CSV hoặc JSON
                </button>
                <input ref={importInput} type="file" accept=".csv,.json" hidden aria-label="Chọn file câu hỏi" onChange={handleImport} />
              </div>
            )}

            {editing && (
              <TestCaseForm
                key={editing === "new" ? "new" : editing.id}
                documents={documents}
                initial={editing === "new" ? null : editing}
                submitLabel={editing === "new" ? "Thêm" : "Lưu thay đổi"}
                onSubmit={handleSave}
                onCancel={() => setEditing(null)}
              />
            )}

            <div className="toolbar">
              <h2>Câu hỏi ({cases.total})</h2>
              <div className="form-actions">
                <select aria-label="Lọc theo loại" value={filters.questionType} onChange={(e) => setFilters((f) => ({ ...f, questionType: e.target.value }))}>
                  <option value="">Mọi loại</option>
                  {Object.entries(QUESTION_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <select aria-label="Lọc theo độ khó" value={filters.difficulty} onChange={(e) => setFilters((f) => ({ ...f, difficulty: e.target.value }))}>
                  <option value="">Mọi độ khó</option>
                  {Object.entries(DIFFICULTY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {cases.items.length === 0 ? (
              <p className="empty-state">Phiên bản này chưa có câu hỏi nào.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Câu hỏi</th>
                      <th>Đáp án chuẩn</th>
                      <th>Loại</th>
                      <th>Độ khó</th>
                      <th>Nguồn</th>
                      <th>
                        <span className="visually-hidden">Thao tác</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {cases.items.map((testCase) => (
                      <tr key={testCase.id}>
                        <td className="cell-wrap">{testCase.question}</td>
                        <td className="cell-wrap">{testCase.ground_truth_answer ?? <span className="muted">(không có đáp án)</span>}</td>
                        <td>{QUESTION_TYPE_LABELS[testCase.question_type]}</td>
                        <td>{DIFFICULTY_LABELS[testCase.difficulty]}</td>
                        <td className="cell-wrap">
                          {testCase.reference_contexts.map((ref, i) => (
                            <div key={i} title={ref.text}>
                              {ref.filename}: “{ref.text.length > 60 ? `${ref.text.slice(0, 60)}…` : ref.text}”
                            </div>
                          ))}
                        </td>
                        <td className="cell-actions">
                          {!frozen && (
                            <>
                              <button type="button" className="button button--ghost button--small" onClick={() => setEditing(testCase)}>
                                Sửa
                              </button>
                              <button type="button" className="button button--danger" onClick={() => handleDelete(testCase)}>
                                Xóa
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function describeErrorShort(error) {
  return error?.message ?? "Đã xảy ra lỗi";
}
