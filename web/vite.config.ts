import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

/**
 * Vite config for the XTV-SupportBot admin SPA.
 *
 * Dev server runs on :5173 and proxies /api/* to the local FastAPI
 * at :8000 (set via API_URL when needed). Build emits into dist/
 * which the production Docker image copies into the FastAPI static
 * mount at /web/.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.API_URL ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    target: 'es2022',
  },
});
