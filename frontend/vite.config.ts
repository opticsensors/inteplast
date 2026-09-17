import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

// https://vitejs.dev/config/
export default defineConfig({
  // Keep the running app's dependency cache separate from ad-hoc Vite servers.
  cacheDir: "node_modules/.vite-app",
  optimizeDeps: {
    // Prepare lazy viewers before navigation can discover new dependencies.
    // They remain lazy browser downloads; this only affects the dev prebundle.
    include: [
      "pdfjs-dist",
      "occt-import-js",
      "three",
      "three/examples/jsm/controls/TrackballControls.js",
      "three/examples/jsm/loaders/GLTFLoader.js",
      "three/examples/jsm/loaders/STLLoader.js",
      "three/examples/jsm/loaders/OBJLoader.js",
      "three/examples/jsm/loaders/PLYLoader.js",
    ],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  plugins: [
    tanstackRouter({
      target: "react",
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
})
