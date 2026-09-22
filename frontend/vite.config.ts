import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig, loadEnv } from "vite"
import { nativePickerPlugin } from "./native-picker"

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, ".."), "")
  return {
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
      nativePickerPlugin(
        env.ASSETS_HOST_PATH ?? "",
        env.VITE_API_URL ?? "http://localhost:8000",
      ),
      tanstackRouter({
        target: "react",
        autoCodeSplitting: true,
      }),
      react(),
      tailwindcss(),
    ],
  }
})
