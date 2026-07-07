import { expect, test } from '@playwright/test';

import { seedBook } from './helpers.js';

// 출판본 시드 + 분류(category) 지정 — 스토어 검색·장르 필터의 전제. seedPublishedBook과 같은
// 원고 본문을 쓰되 category까지 seedBook에 그대로 넘긴다(publish 기본값=price!==null=true).
function seedWithCategory(request, { authorEmail, title, price, category }) {
  return seedBook(request, { authorEmail, title, rawText: '# 1장\n\n본문입니다.', price, category });
}

// 스토어 제목 검색: 입력한 단어가 든 책만 남는다.
test('스토어 검색 — 제목으로 좁히기', async ({ page, request }) => {
  await seedWithCategory(request, { authorEmail: 'search-a@x.com', title: '봄의 시', price: 4000 });
  await seedWithCategory(request, { authorEmail: 'search-b@x.com', title: '여름 소설', price: 5000 });

  await page.goto('/');
  await page.getByPlaceholder('제목 검색').fill('봄');
  await page.getByRole('button', { name: '검색' }).click();

  await expect(page.locator('a', { hasText: '봄의 시' }).first()).toBeVisible();
  await expect(page.locator('a', { hasText: '여름 소설' })).toHaveCount(0);
});

// 장르 필터: 분류를 고르면 해당 분류의 책만 남는다.
test('스토어 장르 필터 — 분류로 좁히기', async ({ page, request }) => {
  await seedWithCategory(request, { authorEmail: 'genre-a@x.com', title: '겨울 시집', price: 4000, category: '시' });
  await seedWithCategory(request, { authorEmail: 'genre-b@x.com', title: '가을 장편', price: 5000, category: '소설' });

  await page.goto('/');
  // 검색으로 두 책이 목록에 있음을 확인(20권 페이지 한계 회피)
  await page.getByPlaceholder('제목 검색').fill('시집');
  await page.getByRole('button', { name: '검색' }).click();
  await expect(page.locator('a', { hasText: '겨울 시집' }).first()).toBeVisible();

  // 검색 비우고 '시' 장르 필터 → 시집만 남고 소설은 사라진다.
  await page.getByPlaceholder('제목 검색').fill('');
  await page.getByRole('button', { name: '검색' }).click();
  await page.getByRole('button', { name: '시', exact: true }).click();

  await expect(page.locator('a', { hasText: '겨울 시집' }).first()).toBeVisible();
  await expect(page.locator('a', { hasText: '가을 장편' })).toHaveCount(0);
});
