import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// Settings come from frontend/.env (see .env.example).
// In development, "/api" calls are forwarded to the FastAPI server, so the browser never hits CORS problems.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    plugins: [react()],
    server: {
      port: Number(env.VITE_DEV_PORT || 5173),
      // 127.0.0.1, not "localhost": on Windows, Node resolves localhost to IPv6 (::1)
      // while uvicorn listens on IPv4, which leaves API calls hanging.
      proxy: { "/api": { target: env.VITE_PROXY_TARGET || "http://127.0.0.1:8000", changeOrigin: true, timeout: 30000, proxyTimeout: 30000 } },
    },
  };
});
