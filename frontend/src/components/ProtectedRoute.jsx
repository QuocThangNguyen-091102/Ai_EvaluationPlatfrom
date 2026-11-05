import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth.js";

// Chặn trang khi chưa đăng nhập. Đây chỉ là tiện ích giao diện: quyền thật được backend kiểm tra ở mọi request.
export default function ProtectedRoute({ children }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <p className="page-message">Đang kiểm tra phiên đăng nhập...</p>;
  }
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}
