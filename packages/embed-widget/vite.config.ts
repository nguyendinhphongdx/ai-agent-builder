import { defineConfig } from "vite";
import preact from "@preact/preset-vite";
import { resolve } from "path";

// Library mode — single self-contained IIFE bundle. Third-party sites drop
// `<script src="embed.js">` and we attach `window.AgentForge`. CSS is inlined
// via shadow DOM at runtime so we never collide with the host page's styles.
export default defineConfig({
  plugins: [preact()],
  build: {
    lib: {
      entry: resolve(__dirname, "src/main.tsx"),
      name: "AgentForge",
      formats: ["iife"],
      fileName: () => "embed.js",
    },
    rollupOptions: {
      output: {
        // Inline asset handling — keep everything in one file.
        inlineDynamicImports: true,
      },
    },
    cssCodeSplit: false,
    minify: "esbuild",
  },
});
