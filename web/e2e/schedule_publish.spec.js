import { expect, test } from '@playwright/test';

import { login } from './helpers.js';

async function tokenFor(request, email, name = '유저') {
  const res = await request.get(
    `/api/auth/test-login?email=${encodeURIComponent(email)}&name=${encodeURIComponent(name)}`,
    { maxRedirects: 0 },
  );
  return new URLSearchParams(res.headers()['location'].split('#')[1]).get('token');
}

// 미출판(DRAFT) + 가격 설정된 책을 시드 (예약 발행 전제 — 가격 필수).
async function seedDraftBook(request, { authorEmail, title, price }) {
  const auth = { Authorization: `Bearer ${await tokenFor(request, authorEmail)}` };
  const book = await (await request.post('/api/books', { headers: auth, data: { title } })).json();
  const id = book.bookId;
  await request.post(`/api/books/${id}/import`, { headers: auth, data: { rawText: '# 1장\n\n본문.' } });
  await request.put(`/api/books/${id}/price`, { headers: auth, data: { amount: price } });
  return id;
}

// 예약 발행 — 미래 시각 입력 → "예약 발행" → 성공 메시지까지. (스케줄러 발동은 스코프 밖)
test('작가: 미래 시각 예약 발행 → 예약 성공 메시지', async ({ page, request }) => {
  const email = 'schedule-author@x.com';
  const id = await seedDraftBook(request, { authorEmail: email, title: '예약발행책', price: 7000 });

  await login(page, email, '예약작가');
  await page.goto(`/studio/${id}`);
  await expect(page.getByRole('heading', { name: '예약발행책' })).toBeVisible();

  // 출판 섹션의 예약 발행 datetime-local (기간 할인의 것과 2개 → 마지막이 예약용)
  await page.locator('input[type="datetime-local"]').last().fill('2030-01-01T09:00');
  await page.getByRole('button', { name: '예약 발행' }).click();

  await expect(page.getByText(/자동 발행 예약됐어요/)).toBeVisible();
});
