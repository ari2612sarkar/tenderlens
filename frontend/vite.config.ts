import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// In dev, proxy /api to the deployed CloudFront URL (set TL_API_ORIGIN).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: process.env.TL_API_ORIGIN
      ? { "/api": { target: process.env.TL_API_ORIGIN, changeOrigin: true } }
      : undefined,
  },
});
