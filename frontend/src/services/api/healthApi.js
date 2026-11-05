import { request } from "./httpClient.js";

// GET /health -> { status: "ok", database: "ok" }
export function getHealth() {
  return request("/health");
}
