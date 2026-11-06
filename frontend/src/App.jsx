import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute.jsx";
import MainLayout from "./layouts/MainLayout.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import DatasetsPage from "./pages/DatasetsPage.jsx";
import DocumentsPage from "./pages/DocumentsPage.jsx";
import EvaluationsPage from "./pages/EvaluationsPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SecurityPage from "./pages/SecurityPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/documents" replace />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="datasets" element={<DatasetsPage />} />
        <Route path="evaluations" element={<EvaluationsPage />} />
        <Route path="security" element={<SecurityPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
