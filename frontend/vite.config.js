// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],

  server: {
    port: 3000,
    // Proxy API calls to the relay server during development so the
    // React dev server and the Flask relay can run on different ports
    // without hitting CORS issues.
    proxy: {
      '/auth':      { target: 'http://localhost:5000', changeOrigin: true },
      '/dashboard': { target: 'http://localhost:5000', changeOrigin: true },
      '/topics':    { target: 'http://localhost:5000', changeOrigin: true },
      '/sessions':  { target: 'http://localhost:5000', changeOrigin: true },
      '/progress':  { target: 'http://localhost:5000', changeOrigin: true },
    },
  },

  build: {
    outDir:    'dist',
    sourcemap: true,
    // Chunk splitting — keeps vendor bundle separate from app code
    rollupOptions: {
      output: {
        manualChunks: {
          vendor:  ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },

  // Env prefix — only VITE_ prefixed vars are exposed to the browser
  envPrefix: 'VITE_',
});
