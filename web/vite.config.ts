import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  // `VITE_ARTIFACT=1 pnpm build` makes a relocatable build (relative asset paths) for publishing as a claude.ai artifact.
  base: process.env.VITE_ARTIFACT ? "./" : "/",
  plugins: [react(), tailwindcss()],
  server: { port: 5180, strictPort: true },
  preview: { port: 5180, strictPort: true },
  worker: { format: "es" },
  build: { chunkSizeWarningLimit: 4000 },
});
