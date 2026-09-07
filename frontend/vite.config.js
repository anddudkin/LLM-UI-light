import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Backend runs on a separate origin (see backend/main.py, CORS is wildcard-open),
// so no dev proxy is configured here.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 8501,
    host: "0.0.0.0",
    cors: true
  },
});
