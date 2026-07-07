import { expect, test } from '@playwright/test';

import { login, seedBook } from './helpers.js';

// AI 추천(데모=키워드 휴리스틱) → 8기준 노출 → 작가가 한 기준 조정 → 저장 → 새로고침해도 유지.
test('작가: 연령 등급 AI 추천 → 조정 → 저장 → 새로고침 후 유지', async ({ page, request }) => {
  const email = 'rating-author@x.com';
  const id = await seedBook(request, {
    authorEmail: email,
    title: '등급테스트책',
    rawText: '# 1장\n\n평범한 하루였다. 주인공은 친구와 산책을 했다.',
  });

  await login(page, email, '등급작가');
  await page.goto(`/studio/${id}`);
  await expect(page.getByRole('heading', { name: '등급테스트책' })).toBeVisible();

  await page.getByRole('button', { name: 'AI로 추천받기' }).click();
  await expect(page.getByText(/등급을 추천했어요/)).toBeVisible();

  // 순한 본문이라 모든 기준이 전체이용가로 나와야 함(데모 휴리스틱 키워드 없음).
  await expect(page.getByText('최종 등급: 전체이용가')).toBeVisible();

  // 작가가 폭력성만 15세로 수동 조정.
  await page.getByLabel('폭력성 등급').selectOption('AGE15');
  await expect(page.getByText('최종 등급: 15세 이용가')).toBeVisible();

  await page.getByRole('button', { name: '등급 저장' }).click();
  await expect(page.getByText('연령 등급이 저장됐어요.')).toBeVisible();

  await page.reload();
  await expect(page.getByLabel('폭력성 등급')).toHaveValue('AGE15');
  await expect(page.getByText('최종 등급: 15세 이용가')).toBeVisible();
});
