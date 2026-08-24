import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// The backend host/port is not fixed. In Docker Compose the proxy target is
// passed via VITE_PROXY_TARGET (e.g. http://backend:8000); locally it defaults
// to http://localhost:8000. The frontend itself calls relative /api paths so no
// backend port is ever hard-coded in application code.
const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: ['metamorphic-kb-dev.luminarconsult.com'],
    proxy: {
      '/api': { target: proxyTarget, changeOrigin: true },
      '/health': { target: proxyTarget, changeOrigin: true },
    },
  },
})
