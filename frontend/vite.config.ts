import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const backendOrigin = process.env.VITE_PROXY_TARGET || "http://127.0.0.1:8082";
const websocketOrigin = backendOrigin.replace(/^http/i, "ws");

export default defineConfig({
  base: "/new/",
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      "/new/api/ws": {
        target: websocketOrigin,
        ws: true,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/new/, "")
      },
      "/new/api": {
        target: backendOrigin,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/new/, "")
      },
      "/api/ws": {
        target: websocketOrigin,
        ws: true,
        changeOrigin: true
      },
      "/api": {
        target: backendOrigin,
        changeOrigin: true
      },
      "/ws": {
        target: websocketOrigin,
        ws: true,
        changeOrigin: true
      }
    }
  }
});
