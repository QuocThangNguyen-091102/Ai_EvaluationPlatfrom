import { createContext, useCallback, useMemo, useRef, useState } from "react";

import ToastStack from "../components/ToastStack.jsx";

const LEAVE_MS = 450;

// Mặc định là không làm gì: trang được render ngoài ToastProvider (ví dụ trong test) vẫn chạy bình thường.
export const ToastContext = createContext({ notify: () => {} });

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id, direction = 0) => {
    setToasts((current) => current.map((toast) => (toast.id === id ? { ...toast, leaving: true, direction } : toast)));
    setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), LEAVE_MS);
  }, []);

  // tone: "success" | "error" | "info". Toast mới nhất nằm đầu danh sách (ở mặt trước của chồng).
  const notify = useCallback(({ tone = "info", title, detail = "" }) => {
    nextId.current += 1;
    const toast = { id: nextId.current, tone, title, detail, leaving: false, direction: 0 };
    setToasts((current) => [toast, ...current]);
  }, []);

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}
