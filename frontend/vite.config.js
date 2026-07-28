import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api and /health to the Flask backend on :5000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:5000",
      "/health": "http://localhost:5000",
    },
  },
});
