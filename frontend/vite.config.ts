import path from "path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      react: path.resolve("./node_modules/react"),
      "react-dom": path.resolve("./node_modules/react-dom"),
    },
  },
  build: {
    target: "esnext",
    cssCodeSplit: true,
    minify: "esbuild",
    sourcemap: false,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("recharts")) return "vendor-charts";
            if (id.includes("axios")) return "vendor-axios";
            return "vendor";
          }
        },
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash].[ext]",
      },
    },
  },
  esbuild: {
    drop: ["console", "debugger"],
  },
  optimizeDeps: {
    include: ["react", "react-dom"],
    exclude: ["@vitejs/plugin-react"],
  },
  server: {
    port: 5173,
    open: true,
    strictPort: true,
  },
  preview: {
    port: 4173,
    open: true,
  },
});
