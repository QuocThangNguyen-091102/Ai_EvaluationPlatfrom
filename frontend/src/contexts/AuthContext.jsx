import { createContext, useCallback, useEffect, useMemo, useState } from "react";

import * as authApi from "../services/api/authApi.js";
import { setAuthToken, setUnauthorizedHandler } from "../services/api/httpClient.js";

const TOKEN_KEY = "ai-eval.token";

// localStorage có thể bị chặn (chế độ riêng tư, chính sách trình duyệt), nên mọi thao tác đều bọc try/catch.
// Lưu ý bảo mật: token trong localStorage đọc được bởi mọi script cùng origin, nên không để chạy script lạ (XSS).
function readStoredToken() {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function storeToken(token) {
  try {
    if (token) {
      window.localStorage.setItem(TOKEN_KEY, token);
    } else {
      window.localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // Không lưu được thì phiên chỉ tồn tại tới khi tải lại trang.
  }
}

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // status: "loading" (đang kiểm tra token đã lưu) | "authenticated" | "anonymous"
  const [state, setState] = useState({ status: "loading", user: null });

  const clearSession = useCallback(() => {
    storeToken(null);
    setAuthToken(null);
    setState({ status: "anonymous", user: null });
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(clearSession);
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  useEffect(() => {
    const token = readStoredToken();
    if (!token) {
      setState({ status: "anonymous", user: null });
      return;
    }
    setAuthToken(token);
    let cancelled = false;
    authApi
      .getCurrentUser()
      .then((user) => {
        if (!cancelled) setState({ status: "authenticated", user });
      })
      .catch(() => {
        if (!cancelled) clearSession();
      });
    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  const login = useCallback(async (email, password) => {
    const { access_token: token } = await authApi.login(email, password);
    setAuthToken(token);
    try {
      const user = await authApi.getCurrentUser();
      storeToken(token);
      setState({ status: "authenticated", user });
    } catch (error) {
      setAuthToken(null);
      throw error;
    }
  }, []);

  const register = useCallback(
    async (email, password) => {
      await authApi.register(email, password);
      await login(email, password);
    },
    [login],
  );

  const value = useMemo(() => ({ ...state, login, register, logout: clearSession }), [state, login, register, clearSession]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
