import { NavLink, Outlet } from "react-router-dom";

import BackendStatus from "../components/BackendStatus.jsx";
import { useAuth } from "../hooks/useAuth.js";

export default function MainLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__brand">AI Evaluation Platform</div>
        <nav className="app-header__nav" aria-label="Điều hướng chính">
          <NavLink to="/documents">Tài liệu</NavLink>
          <NavLink to="/chat">Hỏi đáp</NavLink>
        </nav>
        <div className="app-header__user">
          <span title={user?.email}>{user?.email}</span>
          <button type="button" className="button button--ghost" onClick={logout}>
            Đăng xuất
          </button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <BackendStatus />
      </footer>
    </div>
  );
}
