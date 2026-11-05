import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' — the app is served under a path prefix the platform decides,
// so every asset URL must be relative to the page.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: { outDir: 'dist', emptyOutDir: true },
})
