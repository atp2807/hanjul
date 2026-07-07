import { expect, test } from '@playwright/test';

import { tokenFor } from './helpers.js';

// COVER_DEMO=true 환경 — AI 표지 생성은 API 레벨로만 검증한다.
// UI 버튼은 의도적으로 미노출 상태(LAUNCH.md "AI생성 UI 보류") — novelpotato 실키
// 주입 전까지는 사용자에게 안 보여주기로 한 결정이라, e2e도 그 결정을 존중해서
// 백엔드(DemoCoverGenerator, 백엔드 휴면 코드)만 API로 직접 두드린다.
test('작가: AI 표지 생성 API — DemoCoverGenerator 결정적 SVG 반환 + 책에 반영', async ({ request }) => {
  const email = 'cover-api-author@x.com';
  const auth = { Authorization: `Bearer ${await tokenFor(request, email)}` };

  const book = await (await request.post('/api/books', { headers: auth, data: { title: 'AI표지책' } })).json();
  const bookId = book.bookId;

  const cover = await (
    await request.post(`/api/books/${bookId}/cover`, { headers: auth, data: { prompt: '잔잔한 바다와 등대' } })
  ).json();
  expect(cover.coverUrl).toMatch(/^data:image\/svg\+xml/);

  // 책 요약(/me/books)에도 그 표지가 반영됐는지 — 프론트가 훗날 UI를 열면 바로 쓸 데이터.
  const mine = await (await request.get('/api/me/books', { headers: auth })).json();
  const mineEntry = mine.items.find((b) => b.id === bookId);
  expect(mineEntry.coverUrl).toBe(cover.coverUrl);
});
