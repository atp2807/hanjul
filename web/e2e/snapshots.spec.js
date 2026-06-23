import { expect, test } from '@playwright/test';

// 안전망: 고치기 전 되돌리기 지점을 찍고, 언제든 그 버전으로 복원.
test('되돌리기 지점 저장 → 편집 → 복원', async ({ page }) => {
  await page.goto('/write/snapshot-room');
  const editor = page.locator('.ProseMirror');
  await editor.click();
  await page.keyboard.type('버전 하나 원본');
  await page.getByRole('button', { name: '지점 저장' }).click();
  await expect(page.getByTestId('snapshots')).toContainText('복원');

  // 내용을 완전히 교체 (버튼 클릭으로 빠진 포커스 되돌리기)
  await editor.click();
  await page.keyboard.press('ControlOrMeta+a');
  await page.keyboard.type('완전히 다른 버전 둘');
  await expect(editor).toContainText('완전히 다른 버전 둘');
  await expect(editor).not.toContainText('버전 하나 원본');

  // 저장 지점으로 복원
  await page.getByRole('button', { name: '복원' }).first().click();
  await expect(editor).toContainText('버전 하나 원본');
  await expect(editor).not.toContainText('완전히 다른 버전 둘');
});
