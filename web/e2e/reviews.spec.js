import { expect, test } from '@playwright/test';

import { login, seedPublishedBook } from './helpers.js';

async function tokenFor(request, email, name = '테스트작가') {
  const res = await request.get(
    `/api/auth/test-login?email=${encodeURIComponent(email)}&name=${encodeURIComponent(name)}`,
    { maxRedirects: 0 },
  );
  return new URLSearchParams(res.headers()['location'].split('#')[1]).get('token');
}

// 사회적 증거: 구매한 독자만 평점·리뷰. 상세에 평균·목록 노출.
test('구매자 리뷰 작성 → 평균·목록 노출', async ({ page, request }) => {
  const id = await seedPublishedBook(request, { authorEmail: 'rv-author@x.com', title: '리뷰책', price: 5000 });

  // 독자가 먼저 구매(데모 결제)
  const rt = await tokenFor(request, 'reader-rv@x.com', '리뷰어');
  const rauth = { Authorization: `Bearer ${rt}` };
  const order = await (await request.post('/api/orders', { headers: rauth, data: { bookId: id } })).json();
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

test('미구매자는 리뷰 불가 (403 안내)', async ({ page, request }) => {
  const id = await seedPublishedBook(request, { authorEmail: 'rv-author2@x.com', title: '미구매책', price: 5000 });
  await login(page, 'nobuy@x.com');
  await page.goto(`/books/${id}`);
  await page.getByTestId('review-form').getByLabel('평점').selectOption('5');
  await page.getByRole('button', { name: '리뷰 등록' }).click();
  await expect(page.getByText(/구매한 독자만/)).toBeVisible();
});
