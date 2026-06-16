import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_ATLAS_API_TARGET ?? "http://127.0.0.1:8000";

// Two build targets:
// - Vercel (frontend-only preview): served at the domain root -> base "/",
//   default "dist" output that Vercel expects.
// - FastAPI same-origin (no CORS): served at /app -> base "/app/", built into
//   the Python package so the API can serve it.
const forVercel = Boolean(process.env.VERCEL);

export default defineConfig({
  plugins: [react()],
  base: forVercel ? "/" : "/app/",
  build: {
    outDir: forVercel ? "dist" : "../src/atlas/interfaces/api/spa",
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
