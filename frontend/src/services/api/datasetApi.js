import { request } from "./httpClient.js";

const BASE = "/api/v1";

export function listDatasets() {
  return request(`${BASE}/datasets?limit=100`);
}

export function createDataset(name, description) {
  return request(`${BASE}/datasets`, { method: "POST", json: { name, description: description || null } });
}

export function listVersions(datasetId) {
  return request(`${BASE}/datasets/${datasetId}/versions`);
}

export function createVersion(datasetId, copyFromVersionId) {
  return request(`${BASE}/datasets/${datasetId}/versions`, {
    method: "POST",
    json: copyFromVersionId ? { copy_from_version_id: copyFromVersionId } : {},
  });
}

export function reviewVersion(versionId) {
  return request(`${BASE}/dataset-versions/${versionId}/review`, { method: "POST" });
}

export function listTestCases(versionId, { questionType, difficulty } = {}) {
  const params = new URLSearchParams({ limit: "200" });
  if (questionType) params.set("question_type", questionType);
  if (difficulty) params.set("difficulty", difficulty);
  return request(`${BASE}/dataset-versions/${versionId}/test-cases?${params}`);
}

export function addTestCase(versionId, testCase) {
  return request(`${BASE}/dataset-versions/${versionId}/test-cases`, { method: "POST", json: testCase });
}

export function updateTestCase(caseId, testCase) {
  return request(`${BASE}/test-cases/${caseId}`, { method: "PUT", json: testCase });
}

export function deleteTestCase(caseId) {
  return request(`${BASE}/test-cases/${caseId}`, { method: "DELETE" });
}

export function importTestCases(versionId, file) {
  const formData = new FormData();
  formData.append("file", file);
  return request(`${BASE}/dataset-versions/${versionId}/test-cases/import`, { method: "POST", formData });
}
