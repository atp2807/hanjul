import { expect, test } from '@playwright/test';

import { login } from './helpers.js';

async function tokenFor(request, email) {
  const res = await request.get(`/api/auth/test-login?email=${encodeURIComponent(email)}`, { maxRedirects: 0 });
  return new URLSearchParams(res.headers()['location'].split('#')[1]).get('token');
}

// 유입: 작가가 무료 공개 분량을 정하면 미구매 독자가 그만큼만 본다.
test('무료 미리보기 분량 설정 → 미구매 독자 미리보기 블록 수', async ({ page, request }) => {
  const t = await tokenFor(request, 'preview-lim@x.com');
  const auth = { Authorization: `Bearer ${t}` };
  const book = await (await request.post('/api/books', { headers: auth, data: { title: '유료책' } })).json();
  const id = book.bookId;
  // 5개 블록 본문 + 가격 + 출판
  await request.put(`/api/books/${id}/content`, {
    headers: auth,
    data: { chapters: [{ title: '1장', blocks: [1, 2, 3, 4, 5].map((n) => ({ type: 'P', html: `<p>문단 ${n}</p>` })) }] },
  });
  await request.put(`/api/books/${id}/price`, { headers: auth, data: { amount: 9000 } });
  await request.post(`/api/books/${id}/publish-now`);

  // 작가가 무료 공개 2블록으로 설정 (UI)
  await login(page, 'preview-lim@x.com');
  await page.goto(`/write/${id}`);
  await page.getByTestId('preview-limit-input').fill('2');
  await page.getByRole('button', { name: '저장', exact: true }).click();
  await expect(page.getByText('무료 공개 분량을 저장했어요.')).toBeVisible();

  // 미구매·타인 독자 → 미리보기 2블록만
  const other = await tokenFor(request, 'reader-x@x.com');
  const content = await (
    await request.get(`/api/books/${id}/content`, { headers: { Authorization: `Bearer ${other}` } })
  ).json();
  expect(content.isPreview).toBe(true);
  const blockCount = content.chapters.reduce((n, c) => n + c.blocks.length, 0);
  expect(blockCount).toBe(2);
});
