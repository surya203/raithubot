import { defineConfig, loadEnv } from "vite"
import react from "@vitejs/plugin-react"
import path from "node:path"
import { fileURLToPath } from "node:url"

const dir = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig(({ mode }) => {
  const local = loadEnv(mode, dir, "")
  const backend = loadEnv(mode, path.resolve(dir, "../backend"), "")
  const token = local.INTERNAL_API_TOKEN || backend.INTERNAL_API_TOKEN || ""
  const target = local.API_PROXY_TARGET || "http://127.0.0.1:8000"

  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      proxy: {
        "/api": {
          target,
          changeOrigin: true,
          configure(proxy) {
            proxy.on("proxyReq", (proxyReq) => {
              if (token) proxyReq.setHeader("X-Internal-Token", token)
            })
          },
        },
      },
    },
  }
})
