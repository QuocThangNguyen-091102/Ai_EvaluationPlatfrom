import { request } from "./httpClient.js";

const BASE = "/api/v1/model-configurations";

// Trả { llm_configured, llm_provider, default_llm_model, embedding_provider, embedding_model, prompt_versions }
export function getCapabilities() {
  return request(`${BASE}/capabilities`);
}

export function listConfigurations() {
  return request(`${BASE}?limit=100`);
}

export function createConfiguration(payload) {
  return request(BASE, { method: "POST", json: payload });
}
