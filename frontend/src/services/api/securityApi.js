import { request } from "./httpClient.js";

const BASE = "/api/v1/security";

export function listSecurityTestCases() {
  return request(`${BASE}/test-cases`);
}

export function createSecurityRun({ modelConfigurationId, categories, judgeModel }) {
  return request(`${BASE}/runs`, {
    method: "POST",
    json: {
      model_configuration_id: modelConfigurationId || null,
      categories: categories?.length ? categories : null,
      judge_model: judgeModel?.trim() || null,
    },
  });
}

export function listSecurityRuns() {
  return request(`${BASE}/runs?limit=50`);
}

export function listSecurityResults(runId, { status, severity, category } = {}) {
  const params = new URLSearchParams({ limit: "200" });
  if (status) params.set("status", status);
  if (severity) params.set("severity", severity);
  if (category) params.set("category", category);
  return request(`${BASE}/runs/${runId}/results?${params}`);
}

export function downloadSecurityReport(runId) {
  return request(`${BASE}/runs/${runId}/report?format=csv`, { responseType: "blob" });
}
