import { expect, test } from '@playwright/test';

// 출판 전, 독자가 볼 리더 모습(Pretext 조판)을 그대로 확인.
test('출판 전 미리보기 — 독자 리더로 렌더', async ({ page }) => {
  await page.goto('/write/preview-room');
  const editor = page.locator('.ProseMirror');
  await editor.click();
  await page.keyboard.type('미리보기 본문 문장입니다.');

  await page.getByRole('button', { name: '미리보기' }).click();
  const preview = page.getByTestId('preview-body');
  await expect(page.getByTestId('preview-title')).toBeVisible();
  await expect(preview.getByText('미리보기 본문 문장입니다.')).toBeVisible(); // 리더에 조판됨
  await expect(preview.getByText(/1 \/ \d+/)).toBeVisible(); // 페이지 표시

  await page.getByRole('button', { name: '닫기' }).click();
  await expect(page.getByTestId('preview-title')).toHaveCount(0);
});
