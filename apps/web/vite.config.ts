import path from "node:path";
import * as dotenv from "dotenv";
import { reactRouter } from "@react-router/dev/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

dotenv.config({ path: path.resolve(__dirname, ".env") });

const webBaseUrl = new URL(process.env.VITE_WEB_BASE_URL ?? "http://localhost:3000");
const forwardedHeaders = {
  "X-Forwarded-Host": webBaseUrl.host,
  "X-Forwarded-Proto": webBaseUrl.protocol.slice(0, -1),
};

// Expose only vars starting with VITE_
const viteEnv = Object.keys(process.env)
  .filter((k) => k.startsWith("VITE_"))
  .reduce<Record<string, string>>((a, k) => {
    a[k] = process.env[k] ?? "";
    return a;
  }, {});

export default defineConfig(() => ({
  define: {
    "process.env": JSON.stringify(viteEnv),
  },
  build: {
    assetsInlineLimit: 0,
  },
  plugins: [reactRouter(), tsconfigPaths({ projects: [path.resolve(__dirname, "tsconfig.json")] })],
  resolve: {
    alias: {
      // Next.js compatibility shims used within web
      "next/link": path.resolve(__dirname, "app/compat/next/link.tsx"),
      "next/navigation": path.resolve(__dirname, "app/compat/next/navigation.ts"),
      "next/script": path.resolve(__dirname, "app/compat/next/script.tsx"),
    },
    dedupe: ["react", "react-dom"],
  },
  server: {
    host: "127.0.0.1",
    allowedHosts: [webBaseUrl.hostname],
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        headers: forwardedHeaders,
      },
      "/auth": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        headers: forwardedHeaders,
      },
      "/uploads": {
        target: "http://127.0.0.1:9000",
        changeOrigin: false,
      },
    },
  },
  // No SSR-specific overrides needed; alias resolves to ESM build
}));
