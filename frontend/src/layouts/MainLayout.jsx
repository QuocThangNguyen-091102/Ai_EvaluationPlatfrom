import { Outlet } from "react-router-dom";

import BackendStatus from "../components/BackendStatus.jsx";
import SideRail from "../components/SideRail.jsx";
import { useAuth } from "../hooks/useAuth.js";

export default function MainLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <SideRail email={user?.email} onLogout={logout} />
      <div className="app-column">
        <main className="app-main">
          <Outlet />
        </main>
        <footer className="app-footer">
          <BackendStatus />
        </footer>
      </div>
    </div>
  );
}
