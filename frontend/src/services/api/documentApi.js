import { request } from "./httpClient.js";

const BASE = "/api/v1/documents";

// Trả { items, total, limit, offset }
export function listDocuments({ limit = 10, offset = 0, status } = {}) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (status) {
    params.set("status", status);
  }
  return request(`${BASE}?${params}`);
}

export function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request(BASE, { method: "POST", formData });
}

export function deleteDocument(documentId) {
  return request(`${BASE}/${documentId}`, { method: "DELETE" });
}

// Trả document với status "processing"; chunkSize, chunkOverlap tính bằng từ, bỏ trống thì dùng mặc định.
export function reprocessDocument(documentId, { chunkSize, chunkOverlap } = {}) {
  const json = {};
  if (chunkSize !== undefined) json.chunk_size = chunkSize;
  if (chunkOverlap !== undefined) json.chunk_overlap = chunkOverlap;
  return request(`${BASE}/${documentId}/reprocess`, { method: "POST", json });
}
