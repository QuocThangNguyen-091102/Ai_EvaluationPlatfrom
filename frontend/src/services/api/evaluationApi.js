import { request } from "./httpClient.js";

const BASE = "/api/v1/evaluations";

export function createEvaluation({ datasetVersionId, modelConfigurationId, judgeModel }) {
  return request(BASE, {
    method: "POST",
    json: {
      dataset_version_id: datasetVersionId,
      model_configuration_id: modelConfigurationId || null,
      judge_model: judgeModel?.trim() || null,
    },
  });
}

export function listEvaluations({ status, limit = 50 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set("status", status);
  return request(`${BASE}?${params}`);
}

export function getEvaluation(runId) {
  return request(`${BASE}/${runId}`);
}

export function listResults(runId, { status, category } = {}) {
  const params = new URLSearchParams({ limit: "200" });
  if (status) params.set("status", status);
  if (category) params.set("category", category);
  return request(`${BASE}/${runId}/results?${params}`);
}

export function downloadReport(runId) {
  return request(`${BASE}/${runId}/report?format=csv`, { responseType: "blob" });
}
