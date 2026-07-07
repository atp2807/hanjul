import { expect, test } from '@playwright/test';

import { login, seedBook } from './helpers.js';

// 미출판(DRAFT) + 가격 설정된 책을 시드 (예약 발행 전제 — 가격 필수).
function seedDraftBook(request, { authorEmail, title, price }) {
  return seedBook(request, { authorEmail, title, rawText: '# 1장\n\n본문.', price, publish: false });
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
