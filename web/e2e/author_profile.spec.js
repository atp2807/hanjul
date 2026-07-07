import { expect, test } from '@playwright/test';

import { login, seedPublishedBook, tokenFor } from './helpers.js';

// 작가 브랜드: 스튜디오에서 소개 작성 → 공개 작가 페이지에 소개+출판작 노출.
test('작가 프로필 — 소개 작성 + 출판작 노출', async ({ page, request }) => {
  // 출판작 1권 (작가 = profile-author)
  const bookId = await seedPublishedBook(request, { authorEmail: 'profile-author@x.com', title: '브랜드책', price: 4000 });
  const t = await tokenFor(request, 'profile-author@x.com');
  const me = await (await request.get('/api/me', { headers: { Authorization: `Bearer ${t}` } })).json();

  // 스튜디오에서 소개 저장
  await login(page, 'profile-author@x.com');
  await page.goto('/studio');
  await page.getByTestId('bio-input').fill('한 줄 한 줄 정성껏 씁니다.');
  await page.getByRole('button', { name: '소개 저장' }).click();
  await expect(page.getByText('작가 소개를 저장했어요.')).toBeVisible();

  // 공개 작가 페이지
  await page.goto(`/authors/${me.id}`);
  await expect(page.getByTestId('author-bio')).toContainText('정성껏 씁니다');
  await expect(page.getByTestId('author-books')).toContainText('브랜드책');
});
