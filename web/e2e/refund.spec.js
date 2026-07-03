import { expect, test } from '@playwright/test';

import { login, seedPublishedBook } from './helpers.js';

// 환불 여정: 구매(데모결제) → 서재 확인 → 환불(confirm accept) → 서재에서 사라짐
test('소비자: 구매→서재→환불→서재에서 사라짐', async ({ page, request }) => {
  const title = '환불대상책';
  await seedPublishedBook(request, { authorEmail: 'refund-author@x.com', title, price: 4000 });

  await login(page, 'refund-buyer@x.com', '환불구매자');

  // 구매(데모결제)
  await page.goto('/');
  await page.locator('a', { hasText: title }).first().click();
  await page.getByTestId('withdrawal-consent').locator('input[type="checkbox"]').check();
  await page.getByRole('button', { name: '구매' }).click();
  await expect(page).toHaveURL(/\/read\/[0-9a-f-]+$/);

  // 서재에 있음
  await page.goto('/library');
  await expect(page.locator('text=환불대상책').first()).toBeVisible();

  // 환불 — window.confirm 수락
  page.on('dialog', (d) => d.accept());
  await page.getByRole('button', { name: '환불' }).click();

  // 재방문 시 서재에서 사라짐
  await page.goto('/library');
  await expect(page.locator('text=환불대상책')).toHaveCount(0);
  await expect(page.getByText('아직 구매한 책이 없어요.')).toBeVisible();
});
