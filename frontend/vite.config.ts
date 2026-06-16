import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_ATLAS_API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
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
