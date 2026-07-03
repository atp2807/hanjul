import { expect, test } from '@playwright/test';

// 작가의 "현관문": 한컴/워드에서 쓴 원고(.docx)를 그대로 가져와 편집·출판.
test('DOCX 가져오기 → 에디터 반영(헤딩·서식) + 목차 자동', async ({ page }) => {
  await page.goto('/write/docx-import-room');
  await page.locator('input[accept=".docx"]').setInputFiles('e2e/fixtures/sample.docx');

  const editor = page.locator('.ProseMirror');
  await expect(editor).toContainText('첫 문단입니다');
  await expect(editor.locator('h1')).toHaveText('1장 도입');
  await expect(editor.locator('strong')).toHaveText('굵게'); // 인라인 서식 보존
  await expect(editor.locator('em')).toHaveText('기울임');

  // 가져온 제목이 자동 목차로
  await expect(page.getByTestId('outline')).toContainText('1장 도입');
  await expect(page.getByTestId('outline')).toContainText('2장 전개');
});
