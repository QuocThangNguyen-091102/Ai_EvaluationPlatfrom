import { useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import PasswordField from "../components/PasswordField.jsx";
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
  const cardRef = useRef(null);

  // Lắc thẻ như cái lắc đầu mỗi lần bị từ chối (#062); gỡ class rồi gắn lại để lần sai tiếp theo vẫn lắc.
  useEffect(() => {
    const card = cardRef.current;
    if (!error || !card) return;
    card.classList.remove("auth-card--shake");
    void card.offsetWidth;
    card.classList.add("auth-card--shake");
  }, [error]);

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
      <div className="card auth-card" ref={cardRef}>
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
          <PasswordField
            label="Mật khẩu"
            value={password}
            onChange={setPassword}
            autoComplete={isRegister ? "new-password" : "current-password"}
            showStrength={isRegister}
          />

          {error && (
            <p className="alert alert--error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="button button--primary" disabled={submitting || !email || !password}>
            {submitting && <i className="auth-spinner" aria-hidden="true" />}
            {submitting ? "Đang xử lý..." : isRegister ? "Tạo tài khoản" : "Đăng nhập"}
          </button>
        </form>
      </div>
    </div>
  );
}
