import { expect, test } from '@playwright/test';

import { login, tokenFor } from './helpers.js';

// 제품 핵심 루프: 에디터에서 쓴 글이 원클릭으로 정본→출판→스토어까지 반영.
test('에디터 원클릭 출판 → 정본(챕터 분리) + 스토어 노출', async ({ page, request }) => {
  const t = await tokenFor(request, 'editor-pub@x.com');
  const auth = { Authorization: `Bearer ${t}` };
  const book = await (await request.post('/api/books', { headers: auth, data: { title: '집필책' } })).json();
  const id = book.bookId;
  await request.put(`/api/books/${id}/price`, { headers: auth, data: { amount: 8000 } });

  await login(page, 'editor-pub@x.com'); // 같은 계정으로 브라우저 로그인(소유권)
  await page.goto(`/write/${id}`);
  const editor = page.locator('.ProseMirror');
  await editor.click();

  // 제목으로 챕터 2개 + 본문 (마크다운 입력룰)
  await page.keyboard.type('### 1장 발단');
  await page.keyboard.press('Enter');
  await page.keyboard.type('첫 장 본문입니다.');
  await page.keyboard.press('Enter');
  await page.keyboard.type('### 2장 전개');
  await page.keyboard.press('Enter');
  await page.keyboard.type('둘째 장 본문.');

  await page.getByRole('button', { name: '출판' }).click();
  await expect(page.getByText(/출판 완료/)).toBeVisible();

  // 검증: 정본이 헤딩 기준 2챕터로 분리되어 저장 + 출판 상태
  const meta = await (await request.get(`/api/store/books/${id}`)).json();
  expect(meta.status).toBe('PUBLISHED');

  const content = await (await request.get(`/api/books/${id}/content`)).json();
  expect(content.chapters.length).toBe(2);
  expect(content.chapters[0].title).toBe('1장 발단');
  expect(content.chapters[1].title).toBe('2장 전개');
  expect(JSON.stringify(content)).toContain('첫 장 본문');
  expect(JSON.stringify(content)).toContain('둘째 장 본문');
});

test('빈 글로 출판 차단 (책 내용 손실 방지)', async ({ page, request }) => {
  const t = await tokenFor(request, 'empty-pub@x.com');
  const auth = { Authorization: `Bearer ${t}` };
  const book = await (await request.post('/api/books', { headers: auth, data: { title: '빈책' } })).json();
  const id = book.bookId;
  await request.put(`/api/books/${id}/price`, { headers: auth, data: { amount: 5000 } });

  await login(page, 'empty-pub@x.com');
  await page.goto(`/write/${id}`);
  await page.locator('.ProseMirror').click(); // 아무것도 안 씀
  await page.getByRole('button', { name: '출판' }).click();
  await expect(page.getByText('내용이 없어요. 글을 먼저 쓰세요.')).toBeVisible();

  // 책은 여전히 미출판
  const meta = await (await request.get(`/api/me/books`, { headers: auth })).json();
  expect(meta.items.find((b) => b.id === id).status).toBe('DRAFT');
});

test('남의 책은 덮어쓸 수 없다 (소유권 403)', async ({ request }) => {
  const owner = await tokenFor(request, 'owner-a@x.com');
  const book = await (
    await request.post('/api/books', { headers: { Authorization: `Bearer ${owner}` }, data: { title: '내책' } })
  ).json();
  const intruder = await tokenFor(request, 'intruder-b@x.com');
  const res = await request.put(`/api/books/${book.bookId}/content`, {
    headers: { Authorization: `Bearer ${intruder}` },
    data: { chapters: [{ title: '해킹', blocks: [{ type: 'P', html: '<p>x</p>' }] }] },
  });
  expect(res.status()).toBe(403);
});
