import { expect, test } from '@playwright/test';

import { login, seedPublishedBook } from './helpers.js';

// 사회적 증거: 독자가 출판된 책에 평점·리뷰를 남기고 상세에 노출.
test('리뷰 작성 → 평균·목록 노출', async ({ page, request }) => {
  const id = await seedPublishedBook(request, { authorEmail: 'rv-author@x.com', title: '리뷰책', price: 5000 });

  await login(page, 'reader-rv@x.com', '리뷰어');
  await page.goto(`/books/${id}`);

  // 빈 상태
  await expect(page.getByTestId('review-list')).toContainText('아직 리뷰가 없어요');

  // 평점 4 + 본문 작성
  await page.getByTestId('review-form').getByLabel('평점').selectOption('4');
  await page.getByPlaceholder(/리뷰를 남겨주세요/).fill('술술 읽혀요');
  await page.getByRole('button', { name: '리뷰 등록' }).click();

  // 평균·항목 노출
  await expect(page.getByRole('heading', { name: /리뷰 · ★4/ })).toBeVisible();
  await expect(page.getByTestId('review-list')).toContainText('술술 읽혀요');
  await expect(page.getByTestId('review-list')).toContainText('리뷰어');
});
