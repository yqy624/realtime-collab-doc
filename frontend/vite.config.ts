import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const backendOrigin = process.env.VITE_PROXY_TARGET || "http://127.0.0.1:8081";
const websocketOrigin = backendOrigin.replace(/^http/i, "ws");

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
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
