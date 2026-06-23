import { expect, test } from '@playwright/test';

// 자료 함께 보관: 인물·설정 메모가 책 옆에서 로컬 저장(새로고침 생존).
test('자료 메모 — 입력 후 새로고침 생존', async ({ page }) => {
  await page.goto('/write/notes-room');
  await page.getByTestId('notes').fill('주인공: 김철수, 30세 / 배경: 부산');
  await page.waitForTimeout(600); // y-indexeddb 플러시
  await page.reload();
  await expect(page.getByTestId('notes')).toHaveValue('주인공: 김철수, 30세 / 배경: 부산');
});
