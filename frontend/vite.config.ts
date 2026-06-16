import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_ATLAS_API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  // Built into the FastAPI package so the API serves the SPA same-origin (no
  // CORS). Served at /app during the migration; becomes / once the React app
  // reaches parity with the legacy vanilla UI and the latter is removed.
  base: "/app/",
  build: {
    outDir: "../src/atlas/interfaces/api/spa",
    emptyOutDir: true
  },
  server: {
    port: 5173,
    proxy: {
      "/analyses": apiTarget,
      "/reports": apiTarget,
      "/portfolios": apiTarget,
      "/health": apiTarget,
      "/demo": apiTarget,
      "/agent": apiTarget,
      "/artifacts": apiTarget
    }
  }
});
