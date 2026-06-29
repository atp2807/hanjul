import { expect, test } from '@playwright/test';

import { login } from './helpers.js';

async function tokenFor(request, email) {
  const res = await request.get(`/api/auth/test-login?email=${encodeURIComponent(email)}`, { maxRedirects: 0 });
  return new URLSearchParams(res.headers()['location'].split('#')[1]).get('token');
}

// 출판 전 점검: 누락 항목을 친절히 안내(가격·표지·소개·ISBN).
test('출판 전 체크리스트 — 누락 → 설정 후 충족', async ({ page, request }) => {
  const t = await tokenFor(request, 'checklist@x.com');
  const auth = { Authorization: `Bearer ${t}` };
  const book = await (await request.post('/api/books', { headers: auth, data: { title: '점검책' } })).json();
  const id = book.bookId;

  await login(page, 'checklist@x.com');
  await page.goto(`/write/${id}`);
  await page.locator('.ProseMirror').click();
  await page.keyboard.type('본문 내용');

  const checklist = page.getByTestId('checklist');
  await expect(checklist.locator('[data-check="내용"]')).toHaveAttribute('data-ok', 'true'); // 글 썼으니 충족
  await expect(checklist.locator('[data-check="가격"]')).toHaveAttribute('data-ok', 'false'); // 아직 미설정
  await expect(checklist.locator('[data-check="소개"]')).toHaveAttribute('data-ok', 'false');

  // 스튜디오에서 설정하듯 API로 가격·소개 채우고 새로고침
  await request.put(`/api/books/${id}/price`, { headers: auth, data: { amount: 7000 } });
  await request.put(`/api/books/${id}/meta`, { headers: auth, data: { description: '소개글' } });
  await page.reload();

  await expect(page.getByTestId('checklist').locator('[data-check="가격"]')).toHaveAttribute('data-ok', 'true');
  await expect(page.getByTestId('checklist').locator('[data-check="소개"]')).toHaveAttribute('data-ok', 'true');
});
