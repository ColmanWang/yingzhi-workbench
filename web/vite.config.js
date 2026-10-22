import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8765', '/files': 'http://127.0.0.1:8765' } },
  test: { environment: 'jsdom', setupFiles: './src/test-setup.js', coverage: { provider: 'v8', include: ['src/*.{js,jsx}'], exclude: ['src/main.jsx','src/test-setup.js','src/*.test.jsx'] } },
});
