import { expect, test } from '@playwright/test';

import { login, seedPublishedBook } from './helpers.js';

// 출판 취소: 출판본을 비공개로 내려 스토어에서 사라지게.
test('출판 취소 → 스토어에서 내려감', async ({ page, request }) => {
  const id = await seedPublishedBook(request, { authorEmail: 'unpub@x.com', title: '내릴책', price: 6000 });

  // 스토어에 노출 확인
  expect((await request.get(`/api/store/books/${id}`)).status()).toBe(200);

  await login(page, 'unpub@x.com');
  await page.goto(`/write/${id}`);
  await expect(page.getByRole('button', { name: '출판 취소' })).toBeVisible();
  await page.getByRole('button', { name: '출판 취소' }).click();
  await expect(page.getByText(/출판을 취소했어요/)).toBeVisible();

  // 스토어에서 사라짐(미출판 → 404)
  await expect(async () => {
    expect((await request.get(`/api/store/books/${id}`)).status()).toBe(404);
  }).toPass();
  // 버튼도 사라짐(상태 갱신)
  await expect(page.getByRole('button', { name: '출판 취소' })).toHaveCount(0);
});
