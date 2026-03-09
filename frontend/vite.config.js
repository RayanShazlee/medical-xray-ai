import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/static/react/',
  server: {
    port: 5173,
    proxy: {
      '/upload': 'http://127.0.0.1:7860',
      '/search': 'http://127.0.0.1:7860',
      '/explain-term': 'http://127.0.0.1:7860',
      '/export_pdf': 'http://127.0.0.1:7860',
      '/history': 'http://127.0.0.1:7860',
      '/dashboard': 'http://127.0.0.1:7860',
      '/static': 'http://127.0.0.1:7860',
      '/socket.io': {
        target: 'http://127.0.0.1:7860',
        ws: true,
      },
    },
  },
  build: {
    outDir: '../static/react',
    emptyOutDir: true,
  },
})
