import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    proxy: { "/api": { target: process.env.VITE_PROXY_TARGET ?? "http://localhost:8000" } },
  },
  test: { environment: "jsdom", setupFiles: "./src/testing/setup.ts", globals: true },
});
