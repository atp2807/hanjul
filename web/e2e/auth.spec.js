import { expect, test } from '@playwright/test';

import { login } from './helpers.js';

test('미로그인 헤더는 무료로 시작 버튼을 보인다', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: '무료로 시작', exact: true })).toBeVisible();
});

test('미로그인으로 스튜디오 접근 시 로그인 안내', async ({ page }) => {
  await page.goto('/studio');
  await expect(page.getByText('로그인이 필요해요.')).toBeVisible();
});

test('로그인 → 헤더에 계정 노출, 로그아웃 → 다시 로그인 버튼', async ({ page }) => {
  await login(page, 'auth-user@x.com', '인증유저');
  await expect(page.getByText('인증유저')).toBeVisible();
  await page.getByRole('button', { name: '로그아웃' }).click();
  await expect(page.getByRole('button', { name: '무료로 시작', exact: true })).toBeVisible();
});
