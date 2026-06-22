import { defineConfig } from '@playwright/test';

// 브라우저 E2E — 실 백엔드(28100, 전용 hanjul_e2e DB) + 실 프론트(35200, 28100으로 프록시).
// 인증은 test-login 우회(E2E_LOGIN_ENABLED), 결제·배포는 데모 게이트.
const API = 'http://localhost:28100';
const FRONT = 'http://localhost:35200';
const E2E_DB = 'postgresql+asyncpg://daviy@127.0.0.1:5432/hanjul_e2e';

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.js',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false, // 단일 DB 공유 → 직렬
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: { baseURL: FRONT, trace: 'on-first-retry' },
  webServer: [
    {
      command: '.venv312/bin/uvicorn main:app --host 127.0.0.1 --port 28100',
      cwd: '../backend',
      url: `${API}/api/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        DATABASE_URL: E2E_DB,
        E2E_LOGIN_ENABLED: 'true',
        PAYMENT_DEMO: 'true',
        DISTRIBUTION_DEMO: 'true',
        FRONTEND_URL: FRONT,
        DEBUG: 'false',
      },
    },
    {
      command: 'npm run dev',
      url: FRONT,
      reuseExistingServer: false,
      timeout: 60_000,
      env: { VITE_PORT: '35200', VITE_API_TARGET: API },
    },
  ],
});
