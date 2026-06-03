import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { alphaTab } from '@coderline/alphatab-vite/alphaTabVitePlugin'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const ollamaTarget = env.VITE_OLLAMA_BASE_URL || process.env.VITE_OLLAMA_BASE_URL || 'http://localhost:11434'

  return {
    plugins: [
      react(),
      alphaTab(),
    ],
    server: {
      proxy: {
        // Proxy /api/ollama → Ollama /api/chat (avoids CORS in dev)
        '/api/ollama': {
          target: ollamaTarget,
          changeOrigin: true,
          rewrite: () => '/api/chat',
        },
      },
    },
  }
})
