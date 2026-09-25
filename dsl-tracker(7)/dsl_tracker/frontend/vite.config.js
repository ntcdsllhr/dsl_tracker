import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig(({ command }) => ({
  plugins: [svelte()],
  // Built assets are collected by Django's `collectstatic` into STATIC_ROOT
  // and served under STATIC_URL ("/static/") via WhiteNoise. Without this,
  // Vite writes absolute "/assets/..." paths into index.html, which 404
  // against the real "/static/assets/..." URLs in production — the exact
  // cause of a blank white page with no console/network errors visible
  // unless you check devtools. Dev server (`npm run dev`) still serves from
  // "/" directly, so only the production build needs this.
  base: command === "build" ? "/static/" : "/",
  server: {
    port: 5173,
    proxy: {
      // During `npm run dev`, forward API calls to the Django dev server
      // so the browser only ever talks to one origin.
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
}));
