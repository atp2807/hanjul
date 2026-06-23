import { expect, test } from '@playwright/test';

// 집중 모드: 사이드바·툴바 숨기고 글에만 집중, 해제로 복귀.
test('집중 모드 토글', async ({ page }) => {
  await page.goto('/write/focus-room');
  await expect(page.getByTestId('outline-aside')).toBeVisible();
  await expect(page.getByRole('button', { name: '출판' })).toBeVisible();

  await page.getByRole('button', { name: '집중', exact: true }).click();
  await expect(page.getByTestId('outline-aside')).toHaveCount(0); // 사이드바 숨김
  await expect(page.getByRole('button', { name: '출판' })).toHaveCount(0); // 툴바 숨김
  await expect(page.locator('.ProseMirror')).toBeVisible(); // 에디터는 유지

  await page.getByRole('button', { name: '집중 해제' }).click();
  await expect(page.getByTestId('outline-aside')).toBeVisible();
});
