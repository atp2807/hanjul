import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

import { sharedTestConfig } from '@hanjul/test-utils/vitest-shared';

// 운영자 앱(potato.hanjul.io) — web/ 와 완전 분리된 별도 빌드/배포.
export default defineConfig({
  plugins: [react()],
  test: {
    ...sharedTestConfig,
    exclude: ['**/node_modules/**'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{js,jsx}'],
      exclude: ['src/**/*.test.{js,jsx}', 'src/main.jsx', 'src/App.jsx'],
    },
  },
  server: {
    // web(35173)과 다른 dev 포트
    port: parseInt(process.env.VITE_PORT || '35180', 10),
    proxy: {
      // changeOrigin 금지(인증헤더 유실). 타겟은 백엔드.
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:28000',
      },
    },
  },
});
