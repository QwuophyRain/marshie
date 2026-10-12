import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// base './' keeps asset links relative, so the same build works when FastAPI serves it
// (Raspberry Pi, Mac, Windows) and when Vercel serves it from the site root.
export default defineConfig({
  base: './',
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
  build: { outDir: 'dist', chunkSizeWarningLimit: 700 },
})
