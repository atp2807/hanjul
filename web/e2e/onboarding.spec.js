import { expect, test } from '@playwright/test';

// 첫 출판 가이드: 처음 글쓰기 화면에 안내, 닫으면 다신 안 뜸.
test('온보딩 가이드 — 첫 방문 노출, 닫으면 영구 숨김', async ({ page }) => {
  await page.goto('/write/onboard-room');
  const tips = page.getByTestId('onboarding');
  await expect(tips).toBeVisible();
  await expect(tips).toContainText('3단계면 출판까지');

  await page.getByRole('button', { name: '시작하기' }).click();
  await expect(tips).toHaveCount(0);

  await page.reload();
  await expect(page.getByTestId('onboarding')).toHaveCount(0); // 다신 안 뜸
});
