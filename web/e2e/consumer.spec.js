import { expect, test } from '@playwright/test';

import { login, seedPublishedBook } from './helpers.js';

// 소비자 전 여정: 스토어 → 상세 → 구매(데모결제) → 리더 → 서재
test('소비자: 둘러보기→구매→읽기→서재', async ({ page, request }) => {
  await seedPublishedBook(request, { authorEmail: 'seed-author@x.com', title: '소비자용 책', price: 5000 });

  await login(page, 'buyer@x.com', '구매자');

  // 스토어에서 책 진입
  await page.goto('/');
  await page.locator('a', { hasText: '소비자용 책' }).first().click();
  await expect(page).toHaveURL(/\/books\/[0-9a-f-]+$/);
  await expect(page.getByRole('heading', { name: '소비자용 책' })).toBeVisible();
  await expect(page.getByText('5,000원')).toBeVisible();

  // 구매 → 리더로 이동
  await page.getByRole('button', { name: '구매' }).click();
  await expect(page).toHaveURL(/\/read\/[0-9a-f-]+$/);

  // 서재에 추가됨
  await page.goto('/library');
  await expect(page.locator('text=소비자용 책').first()).toBeVisible();
});

test('소비자: 이미 소유한 책은 재구매 없이 바로 읽기(409→리더)', async ({ page, request }) => {
  await seedPublishedBook(request, { authorEmail: 'seed-author@x.com', title: '재구매 책', price: 3000 });
  await login(page, 'owner@x.com', '소유자');

  // 한 번 구매
  await page.goto('/');
  await page.locator('a', { hasText: '재구매 책' }).first().click();
  await page.getByRole('button', { name: '구매' }).click();
  await expect(page).toHaveURL(/\/read\//);

  // 다시 상세로 → 구매 누르면 이미 소유(409) → 바로 리더
  await page.goto('/');
  await page.locator('a', { hasText: '재구매 책' }).first().click();
  await page.getByRole('button', { name: '구매' }).click();
  await expect(page).toHaveURL(/\/read\//);
});
