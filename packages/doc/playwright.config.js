import { defineConfig } from '@playwright/test';

// 조판(typeset) 실측 e2e — @hanjul/doc 코어 단독 검증. 백엔드/DB/sync-server 전혀 불요.
// vite.harness.config.js 가 서빙하는 정적 하니스(doc-typeset-harness.html)에 접속해
// 실제 chromium 캔버스/DOM 측정 경로를 돌린다.
const PORT = parseInt(process.env.VITE_PORT || '35300', 10);
const BASE_URL = `http://localhost:${PORT}`;

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: true, // DB/외부상태 공유 없음 — 병렬 가능
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  use: { baseURL: BASE_URL, trace: 'on-first-retry' },
  webServer: {
    command: `npx vite --config vite.harness.config.js --port ${PORT}`,
    // 헬스체크는 하니스 파일 자체를 찔러야 한다 — root('/')에는 index.html 이 없어
    // vite 가 404를 내고, playwright 의 url 가용성 체크는 그걸 "미가동"으로 본다.
    url: `${BASE_URL}/doc-typeset-harness.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
