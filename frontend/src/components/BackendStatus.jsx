import { useEffect, useState } from "react";

import { getHealth } from "../services/api/healthApi.js";

// Chỉ báo nhỏ cho biết backend và database có đang phản hồi không (hữu ích khi triển khai và gỡ lỗi).
export default function BackendStatus() {
  const [health, setHealth] = useState({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((data) => !cancelled && setHealth({ state: "ok", data }))
      .catch((error) => !cancelled && setHealth({ state: "error", message: error.message }));
    return () => {
      cancelled = true;
    };
  }, []);

  if (health.state === "loading") {
    return <span className="backend-status">Đang kiểm tra máy chủ...</span>;
  }
  if (health.state === "error") {
    return (
      <span className="backend-status backend-status--error" role="status">
        Máy chủ: không phản hồi ({health.message})
      </span>
    );
  }
  return (
    <span className="backend-status backend-status--ok" role="status">
      Máy chủ: hoạt động · Cơ sở dữ liệu: {health.data.database === "ok" ? "hoạt động" : "lỗi"}
    </span>
  );
}
