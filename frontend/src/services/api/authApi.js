import { request } from "./httpClient.js";

const BASE = "/api/v1/auth";

export function register(email, password) {
  return request(`${BASE}/register`, { method: "POST", json: { email, password }, auth: false });
}

// Trả { access_token, token_type, expires_in }
export function login(email, password) {
  return request(`${BASE}/login`, { method: "POST", json: { email, password }, auth: false });
}

export function getCurrentUser() {
  return request(`${BASE}/me`);
}
