import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { describeError } from "../formatting.js";
import { useAuth } from "../hooks/useAuth.js";

export default function LoginPage() {
  const { status, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const destination = location.state?.from ?? "/documents";

  if (status === "authenticated") {
    return <Navigate to={destination} replace />;
  }

  const isRegister = mode === "register";

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await (isRegister ? register(email, password) : login(email, password));
      navigate(destination, { replace: true });
    } catch (caught) {
      setError(describeError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setError(null);
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1>AI Evaluation Platform</h1>
        <p className="muted">Đánh giá RAG, chất lượng LLM và kiểm thử bảo mật AI.</p>

        <div className="tabs" role="tablist" aria-label="Chế độ">
          <button type="button" role="tab" aria-selected={!isRegister} onClick={() => switchMode("login")}>
            Đăng nhập
          </button>
          <button type="button" role="tab" aria-selected={isRegister} onClick={() => switchMode("register")}>
            Đăng ký
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <label>
            Email
            <input
              type="email"
              name="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Mật khẩu
            <input
              type="password"
              name="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {isRegister && <p className="hint">Mật khẩu cần đủ dài (tối thiểu theo quy định của máy chủ, thường là 8 ký tự).</p>}

          {error && (
            <p className="alert alert--error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="button button--primary" disabled={submitting || !email || !password}>
            {submitting ? "Đang xử lý..." : isRegister ? "Tạo tài khoản" : "Đăng nhập"}
          </button>
        </form>
      </div>
    </div>
  );
}
