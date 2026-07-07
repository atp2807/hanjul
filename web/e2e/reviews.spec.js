import { expect, test } from '@playwright/test';

import { login, seedPublishedBook, tokenFor } from './helpers.js';

// 사회적 증거: 구매한 독자만 평점·리뷰. 상세에 평균·목록 노출.
test('구매자 리뷰 작성 → 평균·목록 노출', async ({ page, request }) => {
  const id = await seedPublishedBook(request, { authorEmail: 'rv-author@x.com', title: '리뷰책', price: 5000 });

  // 독자가 먼저 구매(데모 결제)
  const rt = await tokenFor(request, 'reader-rv@x.com', '리뷰어');
  const rauth = { Authorization: `Bearer ${rt}` };
  const order = await (await request.post('/api/orders', { headers: rauth, data: { bookId: id, withdrawalConsent: true } })).json();
  await request.post(`/api/orders/${order.id}/confirm`, { headers: rauth, data: { pgTxId: 'demo' } });

  await login(page, 'reader-rv@x.com', '리뷰어');
  await page.goto(`/books/${id}`);
  await expect(page.getByTestId('review-list')).toContainText('아직 리뷰가 없어요');

  await page.getByTestId('review-form').getByLabel('평점').selectOption('4');
  await page.getByPlaceholder(/리뷰를 남겨주세요/).fill('술술 읽혀요');
  await page.getByRole('button', { name: '리뷰 등록' }).click();

  await expect(page.getByRole('heading', { name: /리뷰 · 4/ })).toBeVisible();
  await expect(page.getByTestId('review-list')).toContainText('술술 읽혀요');
  await expect(page.getByTestId('review-list')).toContainText('리뷰어');
});

// (책,계정)당 한 건 — 재작성은 갱신(중복 아님). 목록엔 최신 1건만 남는다.
test('구매자 리뷰 재작성 → 갱신(중복 안 됨)', async ({ page, request }) => {
  const id = await seedPublishedBook(request, { authorEmail: 'rv-author3@x.com', title: '재작성책', price: 5000 });

  const rt = await tokenFor(request, 'reader-redo@x.com', '재작성러');
  const rauth = { Authorization: `Bearer ${rt}` };
  const order = await (await request.post('/api/orders', { headers: rauth, data: { bookId: id, withdrawalConsent: true } })).json();
  await request.post(`/api/orders/${order.id}/confirm`, { headers: rauth, data: { pgTxId: 'demo' } });

  await login(page, 'reader-redo@x.com', '재작성러');
  await page.goto(`/books/${id}`);

  // 첫 리뷰 (4점)
  await page.getByTestId('review-form').getByLabel('평점').selectOption('4');
  await page.getByPlaceholder(/리뷰를 남겨주세요/).fill('처음엔 그저 그랬어요');
  await page.getByRole('button', { name: '리뷰 등록' }).click();
  await expect(page.getByRole('heading', { name: /리뷰 · 4 \(1\)/ })).toBeVisible();
  await expect(page.getByTestId('review-list')).toContainText('처음엔 그저 그랬어요');

  // 재작성 (2점·다른 내용) → 갱신
  await page.getByTestId('review-form').getByLabel('평점').selectOption('2');
  await page.getByPlaceholder(/리뷰를 남겨주세요/).fill('다시 읽으니 아쉬웠어요');
  await page.getByRole('button', { name: '리뷰 등록' }).click();

  // 평균·개수가 2·(1)로 갱신 → 리뷰는 여전히 한 건, 내용은 최신으로 교체
  await expect(page.getByRole('heading', { name: /리뷰 · 2 \(1\)/ })).toBeVisible();
  await expect(page.getByTestId('review-list')).toContainText('다시 읽으니 아쉬웠어요');
  await expect(page.getByTestId('review-list')).not.toContainText('처음엔 그저 그랬어요');
  await expect(page.getByTestId('review-list')).toContainText('(수정됨)');
});

test('미구매자는 리뷰 불가 (403 안내)', async ({ page, request }) => {
  const id = await seedPublishedBook(request, { authorEmail: 'rv-author2@x.com', title: '미구매책', price: 5000 });
  await login(page, 'nobuy@x.com');
  await page.goto(`/books/${id}`);
  await page.getByTestId('review-form').getByLabel('평점').selectOption('5');
  await page.getByRole('button', { name: '리뷰 등록' }).click();
  await expect(page.getByText(/구매한 독자만/)).toBeVisible();
});
