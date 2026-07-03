import { expect, test } from '@playwright/test';

import { login } from './helpers.js';

// 개인정보 열람권 — 내 정보 JSON 내려받기 트리거 확인
test('설정: 내 정보 내려받기(다운로드 트리거)', async ({ page }) => {
  await login(page, 'export-user@x.com', '내보내기유저');
  await page.goto('/settings');

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: '내 정보 내려받기' }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/\.json$/);
});

// 회원 탈퇴 — 2단계 확인 후 로그아웃 상태로 이동
test('설정: 회원 탈퇴(2단계 확정)→로그아웃', async ({ page }) => {
  await login(page, 'withdraw-user@x.com', '탈퇴유저');
  await page.goto('/settings');

  // 1단계: 탈퇴 버튼 → 확인 안내
  await page.getByRole('button', { name: '회원 탈퇴' }).click();
  await expect(page.getByText('정말 탈퇴하시겠어요?')).toBeVisible();

  // 2단계: 확정 → 로그아웃 상태(헤더에 '무료로 시작')
  await page.getByRole('button', { name: '네, 탈퇴할게요' }).click();
  await expect(page.getByRole('button', { name: '무료로 시작', exact: true })).toBeVisible();
});
