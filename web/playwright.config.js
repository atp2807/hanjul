import { defineConfig } from '@playwright/test';

import { BACKEND_PY, databaseUrl } from './e2e/db.js';

// 브라우저 E2E — 실 백엔드(28100, 전용 e2e DB) + 실 프론트(35200, 28100으로 프록시).
// 인증은 test-login 우회(E2E_LOGIN_ENABLED), 결제·배포는 데모 게이트.
const API = 'http://localhost:28100';
const FRONT = 'http://localhost:35200';

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.js',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false, // 단일 DB 공유 → 직렬
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  use: { baseURL: FRONT, trace: 'on-first-retry' },
  webServer: [
    {
      command: `${BACKEND_PY} -m uvicorn main:app --host 127.0.0.1 --port 28100`,
      cwd: '../backend',
      url: `${API}/api/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        DATABASE_URL: databaseUrl(),
        E2E_LOGIN_ENABLED: 'true',
        PAYMENT_DEMO: 'true',
        DISTRIBUTION_DEMO: 'true',
        COVER_DEMO: 'true',
        FRONTEND_URL: FRONT,
        DEBUG: 'false',
      },
    },
    {
      // CRDT 동기화 릴레이 서버 (TCP 포트로 준비 감지)
      command: 'node sync-server.mjs',
      port: 1236,
      reuseExistingServer: false,
      timeout: 30_000,
      env: { SYNC_PORT: '1236' },
    },
    {
      command: 'npm run dev',
      url: FRONT,
      reuseExistingServer: false,
      timeout: 60_000,
      env: { VITE_PORT: '35200', VITE_API_TARGET: API, VITE_SYNC_URL: 'ws://localhost:1236' },
    },
  ],
});
