import { useEffect, useState } from "react";

import { getHealth } from "./services/api/healthApi.js";

export default function App() {
  const [health, setHealth] = useState({ state: "loading" });

  useEffect(() => {
    getHealth()
      .then((data) => setHealth({ state: "ok", data }))
      .catch((error) => setHealth({ state: "error", message: error.message }));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "2rem" }}>
      <h1>AI Evaluation Platform</h1>
      <h2>Trạng thái backend</h2>
      {health.state === "loading" && <p>Đang kiểm tra...</p>}
      {health.state === "ok" && (
        <p>
          Backend: <strong>{health.data.status}</strong> | Database: <strong>{health.data.database}</strong>
        </p>
      )}
      {health.state === "error" && <p role="alert">Lỗi: {health.message}</p>}
    </main>
  );
}
