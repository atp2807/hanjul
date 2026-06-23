import { expect, test } from '@playwright/test';

// 동기부여: 목표 글자수 설정 → 진행 표시 → 달성 시 표시.
test('목표/진행 막대 — 달성 표시', async ({ page }) => {
  await page.goto('/write/goal-room');
  await page.getByTestId('goal-input').fill('5');

  const editor = page.locator('.ProseMirror');
  await editor.click();
  await page.keyboard.type('여섯글자입력'); // 6자 > 5

  await expect(page.getByTestId('progress')).toContainText('목표 달성');
  await expect(page.getByTestId('progress')).toContainText('/ 5자');
});
