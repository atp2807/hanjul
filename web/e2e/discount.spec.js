import { expect, test } from '@playwright/test';

import { login, seedPublishedBook } from './helpers.js';

// 기간 할인: 작가가 설정 → 스토어 상세에 할인가(원가 취소선) 노출.
test('기간 할인 설정 → 상세에 할인가 표시', async ({ page, request }) => {
  const id = await seedPublishedBook(request, { authorEmail: 'disc-author@x.com', title: '할인책', price: 10000 });

  await login(page, 'disc-author@x.com');
  await page.goto(`/studio/${id}`);
  await page.getByPlaceholder('할인가').fill('6000');
  // 내일까지
  const until = new Date(Date.now() + 86400000);
  const local = new Date(until.getTime() - until.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  await page.locator('input[type="datetime-local"]').fill(local);
  await page.getByRole('button', { name: '할인 저장' }).click();
  await expect(page.getByText('할인이 설정됐어요.')).toBeVisible();

  // 스토어 상세: 할인가 + 원가 취소선
  await page.goto(`/books/${id}`);
  const price = page.getByTestId('price');
  await expect(price).toContainText('6,000원');
  await expect(price).toContainText('10,000원'); // 취소선 원가
  await expect(price).toContainText('기간 할인');
});
