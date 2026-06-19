import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    // 웰노운/흔한 dev 포트(5173) 회피 — server_hardening_checklist
    port: parseInt(process.env.VITE_PORT || '35173', 10),
    proxy: {
      // changeOrigin: true 금지 — Host 변경 시 인증 헤더 유실(vite_proxy_changeorigin_auth_loss)
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:28000',
      },
    },
  },
  resolve: {
    alias: { '@': '/src' },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    exclude: ['**/node_modules/**'],
  },
});
