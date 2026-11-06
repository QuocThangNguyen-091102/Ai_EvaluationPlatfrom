import { request } from "./httpClient.js";

const BASE = "/api/v1/benchmarks";

export function createBenchmark({ name, datasetVersionId, variedVariable, modelConfigurationIds, judgeModel }) {
  return request(BASE, {
    method: "POST",
    json: {
      name,
      dataset_version_id: datasetVersionId,
      varied_variable: variedVariable,
      model_configuration_ids: modelConfigurationIds,
      judge_model: judgeModel?.trim() || null,
    },
  });
}

export function listBenchmarks() {
  return request(`${BASE}?limit=50`);
}

export function getBenchmark(benchmarkId) {
  return request(`${BASE}/${benchmarkId}`);
}

export function downloadBenchmarkReport(benchmarkId) {
  return request(`${BASE}/${benchmarkId}/report?format=csv`, { responseType: "blob" });
}
