import { expect, test } from '@playwright/test';

import { seedPublishedBook } from './helpers.js';

// 독서 메모: 읽으며 적은 메모가 이 기기에 저장(새로고침 생존).
test('독서 메모 — 입력 후 새로고침 생존', async ({ page, request }) => {
  const id = await seedPublishedBook(request, { authorEmail: 'memo-author@x.com', title: '메모책', price: 0 });
  await page.goto(`/read/${id}`);
  await page.getByTestId('reader-memo').fill('주인공의 선택이 인상적');
  await page.reload();
  await expect(page.getByTestId('reader-memo')).toHaveValue('주인공의 선택이 인상적');
});
