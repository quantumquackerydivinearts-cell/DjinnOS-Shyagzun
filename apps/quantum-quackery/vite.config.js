// atelier-desktop/vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const IS_ELECTRON = process.env.ELECTRON === "true";

export default defineConfig({
  plugins: [react()],

  // When building for Electron, use relative asset paths
  base: IS_ELECTRON ? "./" : "/",

  build: {
    outDir: "dist",
    emptyOutDir: true,
    // Electron needs relative paths, not absolute
    assetsDir: "assets",
  },

  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // In dev, proxy API calls to your local FastAPI instance
      // so you don't hit CORS issues during development
      "/v1": {
        target: "http://localhost:8080",
        changeOrigin: true,
        secure: false,
      },
      "/ready": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },

  define: {
    // Expose build-time env to the app
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    __IS_ELECTRON__: JSON.stringify(IS_ELECTRON),
  },
});
