import { useContext } from "react";

import { ToastContext } from "../contexts/ToastContext.jsx";

export function useToast() {
  return useContext(ToastContext);
}
