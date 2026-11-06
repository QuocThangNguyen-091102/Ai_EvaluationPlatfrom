import { useCallback, useEffect, useRef, useState } from "react";

import {
  STATUS_LABELS,
  describeError,
  formatContentType,
  formatDateTime,
  formatFileSize,
} from "../formatting.js";
import { deleteDocument, listDocuments, reprocessDocument, uploadDocument } from "../services/api/documentApi.js";

const PAGE_SIZE = 10;
const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt"];
const POLL_INTERVAL_MS = 3000;
// Dừng tự làm mới sau chừng này lần để không gọi API mãi khi tài liệu không đổi trạng thái; người dùng vẫn có nút Làm mới.
const MAX_POLLS = 20;
const IN_PROGRESS = new Set(["uploaded", "processing"]);

function hasAcceptedExtension(name) {
  return ACCEPTED_EXTENSIONS.some((extension) => name.toLowerCase().endsWith(extension));
}

export default function DocumentsPage() {
  const [page, setPage] = useState({ items: [], total: 0 });
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [uploads, setUploads] = useState([]); // kết quả từng file vừa tải: { name, ok, message }
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [pollCount, setPollCount] = useState(0);
  const fileInput = useRef(null);

  const load = useCallback(async () => {
    try {
      const result = await listDocuments({ limit: PAGE_SIZE, offset });
      setPage(result);
      setLoadError(null);
      // Xóa hết ở trang cuối thì lùi về trang trước.
      if (result.items.length === 0 && result.total > 0 && offset > 0) {
        setOffset(Math.max(0, offset - PAGE_SIZE));
      }
    } catch (error) {
      setLoadError(describeError(error));
    } finally {
      setLoading(false);
    }
  }, [offset]);

  useEffect(() => {
    load();
  }, [load]);

  const anyInProgress = page.items.some((item) => IN_PROGRESS.has(item.status));
  useEffect(() => {
    if (!anyInProgress || pollCount >= MAX_POLLS) return undefined;
    const timer = setTimeout(() => {
      setPollCount((count) => count + 1);
      load();
    }, POLL_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [anyInProgress, pollCount, load]);

  async function handleFiles(fileList) {
    const files = Array.from(fileList);
    if (files.length === 0) return;
    setUploading(true);
    const results = [];
    for (const file of files) {
      if (!hasAcceptedExtension(file.name)) {
        results.push({ name: file.name, ok: false, message: "Chỉ chấp nhận file PDF, DOCX hoặc TXT" });
        continue;
      }
      try {
        await uploadDocument(file);
        results.push({ name: file.name, ok: true, message: "Đã tải lên" });
      } catch (error) {
        results.push({ name: file.name, ok: false, message: describeError(error) });
      }
    }
    setUploads(results);
    setUploading(false);
    setPollCount(0);
    setOffset(0);
    await load();
    if (fileInput.current) fileInput.current.value = "";
  }

  async function handleDelete(document) {
    if (!window.confirm(`Xóa tài liệu "${document.filename}"? Thao tác này không hoàn tác được.`)) return;
    try {
      await deleteDocument(document.id);
      await load();
    } catch (error) {
      setLoadError(describeError(error));
    }
  }

  async function handleReprocess(document) {
    try {
      await reprocessDocument(document.id);
      setPollCount(0);
      await load();
    } catch (error) {
      setLoadError(describeError(error));
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    handleFiles(event.dataTransfer.files);
  }

  const lastPage = Math.max(0, Math.ceil(page.total / PAGE_SIZE) - 1);
  const currentPage = Math.floor(offset / PAGE_SIZE);

  return (
    <section>
      <h1>Tài liệu</h1>
      <p className="muted">Tải lên tài liệu PDF, DOCX hoặc TXT (UTF-8) để hệ thống xử lý và dùng cho hỏi đáp.</p>

      <div
        className={`dropzone${dragging ? " dropzone--active" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <p>Kéo thả file vào đây hoặc</p>
        <button type="button" className="button button--primary" disabled={uploading} onClick={() => fileInput.current?.click()}>
          {uploading ? "Đang tải lên..." : "Chọn file"}
        </button>
        <input
          ref={fileInput}
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS.join(",")}
          hidden
          aria-label="Chọn file tài liệu"
          onChange={(event) => handleFiles(event.target.files)}
        />
      </div>

      {uploads.length > 0 && (
        <ul className="upload-results" aria-label="Kết quả tải lên">
          {uploads.map((result, index) => (
            <li key={`${result.name}-${index}`} className={result.ok ? "upload-results__ok" : "upload-results__error"}>
              <strong>{result.name}</strong>: {result.message}
            </li>
          ))}
        </ul>
      )}

      {loadError && (
        <p className="alert alert--error" role="alert">
          {loadError}
        </p>
      )}

      <div className="toolbar">
        <h2>Danh sách ({page.total})</h2>
        <button type="button" className="button button--ghost" onClick={() => { setPollCount(0); load(); }}>
          Làm mới
        </button>
      </div>

      {loading ? (
        <p className="page-message">Đang tải danh sách...</p>
      ) : page.items.length === 0 ? (
        <p className="empty-state">Chưa có tài liệu nào. Hãy tải lên tài liệu đầu tiên của bạn.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Tên</th>
                <th>Loại</th>
                <th>Dung lượng</th>
                <th>Trạng thái</th>
                <th>Số đoạn</th>
                <th>Tải lên lúc</th>
                <th>
                  <span className="visually-hidden">Thao tác</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((document) => (
                <tr key={document.id}>
                  <td className="cell-name" title={document.filename}>
                    {document.filename}
                  </td>
                  <td>{formatContentType(document.content_type)}</td>
                  <td>{formatFileSize(document.size_bytes)}</td>
                  <td>
                    <span className={`badge badge--${document.status}`}>{STATUS_LABELS[document.status] ?? document.status}</span>
                    {document.status === "failed" && document.error_message && (
                      <div className="cell-error">{document.error_message}</div>
                    )}
                  </td>
                  <td>{document.chunk_count}</td>
                  <td>{formatDateTime(document.created_at)}</td>
                  <td className="cell-actions">
                    {(document.status === "ready" || document.status === "failed") && (
                      <button type="button" className="button button--ghost button--small" onClick={() => handleReprocess(document)}>
                        Xử lý lại
                      </button>
                    )}
                    <button type="button" className="button button--danger" onClick={() => handleDelete(document)}>
                      Xóa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {page.total > PAGE_SIZE && (
        <nav className="pagination" aria-label="Phân trang">
          <button type="button" className="button button--ghost" disabled={currentPage === 0} onClick={() => setOffset(offset - PAGE_SIZE)}>
            Trước
          </button>
          <span>
            Trang {currentPage + 1} / {lastPage + 1}
          </span>
          <button
            type="button"
            className="button button--ghost"
            disabled={currentPage >= lastPage}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Sau
          </button>
        </nav>
      )}
    </section>
  );
}
