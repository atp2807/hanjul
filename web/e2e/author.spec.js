import { expect, test } from '@playwright/test';

import { login } from './helpers.js';

// 작가 전 여정: 책 생성 → 원고 → 가격 → ISBN → 즉시출간 → EPUB 다운로드 → 서점 배포
test('작가: 생성→출간→서점 배포까지 한 흐름', async ({ page }) => {
  await login(page, 'author@x.com', '글쓴이');

  // 책 생성
  await page.goto('/studio');
  await page.getByPlaceholder('새 책 제목').fill('E2E 출간 테스트');
  await page.getByRole('button', { name: '새 책 만들기' }).click();
  await expect(page).toHaveURL(/\/studio\/[0-9a-f-]+$/);
  await expect(page.getByRole('heading', { name: 'E2E 출간 테스트' })).toBeVisible();

  // 원고 추가
  await page.getByPlaceholder(/장 제목/).fill('# 첫 장\n\n안녕하세요. 본문입니다.');
  await page.getByRole('button', { name: '장 추가' }).click();
  await expect(page.getByText(/블록이 새 장으로 추가/)).toBeVisible();

  // AI 표지 생성 (데모) → 미리보기 이미지 노출
  await page.getByPlaceholder(/표지 분위기/).fill('잔잔한 한국 에세이, 따뜻한 색감');
  await page.getByRole('button', { name: 'AI 표지 생성' }).click();
  await expect(page.getByText('표지가 생성됐어요.')).toBeVisible();
  await expect(page.getByRole('img', { name: '표지' })).toBeVisible();

  // 책 정보 (부제·소개·분류)
  await page.getByPlaceholder('부제 (선택)').fill('E2E 부제');
  await page.getByPlaceholder(/책 소개/).fill('자동 테스트로 만든 책 소개.');
  await page.getByRole('combobox').first().selectOption('에세이');
  await page.getByRole('button', { name: '정보 저장' }).click();
  await expect(page.getByText('책 정보가 저장됐어요.')).toBeVisible();

  // 가격
  await page.locator('input[type=number]').fill('9000');
  await page.getByRole('button', { name: '가격 저장' }).click();
  await expect(page.getByText('가격이 저장됐어요.')).toBeVisible();

  // ISBN
  await page.getByPlaceholder('978-89-...').fill('9788912345678');
  await page.getByRole('button', { name: 'ISBN 저장' }).click();
  await expect(page.getByText('ISBN이 저장됐어요.')).toBeVisible();

  // EPUB 다운로드
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'EPUB 내려받기' }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/\.epub$/);

  // 즉시 출간
  await page.getByRole('button', { name: '즉시 출간' }).click();
  await expect(page.getByText(/즉시 출간됐어요/)).toBeVisible();

  // 서점 배포 (출판본 한정 섹션)
  await expect(page.getByText('서점 배포')).toBeVisible();
  await page.getByRole('button', { name: '배포 전송' }).click();
  await expect(page.getByRole('listitem').filter({ hasText: '교보문고' }).getByText('전송됨')).toBeVisible();

  // 스토어에 노출되는지
  await page.goto('/');
  await expect(page.locator('a', { hasText: 'E2E 출간 테스트' }).first()).toBeVisible();
});
