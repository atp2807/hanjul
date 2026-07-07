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
  // jszip(EPUB 가져오기)·@chenglou/pretext(@hanjul/doc 조판 코어의 의존성 — 워크스페이스
  // 링크 패키지라 스캔에서 늦게 발견됨)를 초기 최적화 패스에 포함 — 런타임 늦은 발견 시
  // 발생하는 vite 재-최적화(모노레포에서 hoist된 react 경로 오인 → 504 Outdated Optimize Dep) 회피.
  optimizeDeps: {
    include: ['jszip', '@chenglou/pretext', '@chenglou/pretext/rich-inline'],
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    exclude: ['**/node_modules/**', '**/e2e/**'],
    coverage: {
      provider: 'v8',
      // 유닛(vitest) 커버리지는 src 앱 코드만. 아래는 단위테스트 대상이 아님:
      //  - e2e/·config: Playwright/빌드, 진입점 App·main, *.test, 셋업, sync-server
      //  - writer 에디터: ProseMirror 통합 → e2e/통합에서 커버
      include: ['src/**/*.{js,jsx}'],
      exclude: [
        'src/**/*.test.{js,jsx}',
        'src/test/**',
        'src/main.jsx',
        'src/App.jsx',
        'src/sampleBook.js',
      ],
    },
  },
});
