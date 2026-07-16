import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_ATLAS_API_TARGET ?? "http://127.0.0.1:8000";

// Both deployment targets serve the React app at the domain root. Vercel uses
// its server-side /api/atlas proxy; the FastAPI bundle calls same-origin API
// routes directly and is emitted into the Python package.
const forVercel = Boolean(process.env.VERCEL);

export default defineConfig({
  plugins: [react()],
  base: "/",
  define: {
    "import.meta.env.VITE_ATLAS_RUNTIME": JSON.stringify(
      forVercel ? "proxy" : "same-origin"
    )
  },
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
