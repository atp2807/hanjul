import { expect, test } from '@playwright/test';

import { login, tokenFor } from './helpers.js';

// 소개문 추천: 본문에서 소개문을 뽑아 소개 칸을 채움.
test('소개문 추천 → 본문 발췌로 소개 채움', async ({ page, request }) => {
  const t = await tokenFor(request, 'blurb-author@x.com');
  const auth = { Authorization: `Bearer ${t}` };
  const book = await (await request.post('/api/books', { headers: auth, data: { title: '소개책' } })).json();
  const id = book.bookId;
  await request.post(`/api/books/${id}/import`, { headers: auth, data: { rawText: '# 1장\n\n주인공은 새벽에 길을 나섰다.' } });

  await login(page, 'blurb-author@x.com');
  await page.goto(`/studio/${id}`);
  await page.getByRole('button', { name: '소개문 추천' }).click();
  await expect(page.getByPlaceholder('책 소개 (스토어 상세에 노출)')).toHaveValue(/주인공은 새벽에/);
});
