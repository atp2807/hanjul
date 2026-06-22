import { expect, test } from '@playwright/test';

// 로컬우선의 핵심 보증: 입력은 즉시 로컬(IndexedDB)에 영속 → 새로고침/크래시에도 안 날아감.
test('입력 → 새로고침 후에도 남아있다 (안 날아감)', async ({ page }) => {
  await page.goto('/write/e2e-keep');
  const editor = page.locator('.ProseMirror');
  await editor.click();
  await page.keyboard.type('첫 문장은 절대 사라지면 안 된다');
  await expect(editor).toContainText('절대 사라지면 안 된다');

  // 저장 상태가 눈에 보인다 (안 날아감 체감)
  await expect(page.getByTestId('writer-status')).toContainText('저장됨');

  await page.waitForTimeout(600); // y-indexeddb 로컬 플러시 대기
  await page.reload();

  // 재마운트 → 서버 아닌 로컬에서 복원
  await expect(page.locator('.ProseMirror')).toContainText('절대 사라지면 안 된다');
});

test('서식 단축키 → 정본으로 직렬화 가능한 마크 적용', async ({ page }) => {
  await page.goto('/write/e2e-fmt');
  const editor = page.locator('.ProseMirror');
  await editor.click();
  await page.keyboard.type('굵게');
  await page.keyboard.press('ControlOrMeta+a');
  await page.keyboard.press('ControlOrMeta+b'); // strong 토글 (Mod = mac Cmd)
  await expect(editor.locator('strong')).toHaveText('굵게');
});
