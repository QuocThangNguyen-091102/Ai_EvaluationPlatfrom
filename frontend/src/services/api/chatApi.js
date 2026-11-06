import { request } from "./httpClient.js";

const BASE = "/api/v1/chat";

// Trả { session_id, message_id, answer, insufficient_context, mode, citations, sources, metrics, model_configuration_id }
export function askQuestion({ question, sessionId, modelConfigurationId }) {
  const json = { question };
  if (sessionId) json.session_id = sessionId;
  if (modelConfigurationId) json.model_configuration_id = modelConfigurationId;
  return request(`${BASE}/messages`, { method: "POST", json });
}

export function listSessions({ limit = 50, offset = 0 } = {}) {
  return request(`${BASE}/sessions?limit=${limit}&offset=${offset}`);
}

export function getSessionMessages(sessionId) {
  return request(`${BASE}/sessions/${sessionId}/messages`);
}

export function deleteSession(sessionId) {
  return request(`${BASE}/sessions/${sessionId}`, { method: "DELETE" });
}
