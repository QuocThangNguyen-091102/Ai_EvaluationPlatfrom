import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Cần để truy cập được từ ngoài container khi chạy bằng Docker.
    host: true,
  },
});
