import { expect, test } from '@playwright/test';

import { login, seedPublishedBook } from './helpers.js';

// 개정판 알림: 이미 출판된 책을 작가가 다시 출판(재발행)하면 백엔드가 '개정판'으로
// 간주해 구매자에게 알림을 보낸다(catalog publish_now → _notify_buyers_revision).
// 프론트에서 이미 출판된 책의 재발행은 에디터(/write/:id)의 '출판' 버튼이 담당
// (StudioEditorPage의 '즉시 출간' 버튼은 미출판 상태에서만 노출됨).
test('재발행(개정판) → 구매자에게 개정판 알림', async ({ page, request }) => {
  const authorEmail = 'republish-author@x.com';
  const title = '개정판알림책';
  const bookId = await seedPublishedBook(request, { authorEmail, title, price: 5000 });

  // 독자 구매(데모결제) — 구매자여야 개정판 알림 대상이 된다.
  await login(page, 'republish-reader@x.com', '개정독자');
  await page.goto('/');
  await page.locator('a', { hasText: title }).first().click();
  await page.getByTestId('withdrawal-consent').locator('input[type="checkbox"]').check();
  await page.getByRole('button', { name: '구매' }).click();
  await expect(page).toHaveURL(/\/read\//);

  // 작가로 전환 → 에디터에서 원고 수정 후 '출판'(= 이미 출판본이라 개정판 재발행)
  await login(page, authorEmail, '개정작가');
  await page.goto(`/write/${bookId}`);
  const editor = page.locator('.ProseMirror');
  await editor.click();
  await page.keyboard.type('### 개정 장');
  await page.keyboard.press('Enter');
  await page.keyboard.type('개정판에서 새로 더한 본문입니다.');
  // 출판된 책이라 '출판 취소' 버튼도 함께 있어 exact로 '출판' 버튼만 지정.
  await page.getByRole('button', { name: '출판', exact: true }).click();
  await expect(page.getByText(/출판 완료/)).toBeVisible();

  // 독자로 다시 전환 → 벨에 개정판 알림 1건
  await login(page, 'republish-reader@x.com', '개정독자');
  await page.reload();
  await expect(page.getByTestId('notif-badge')).toHaveText('1');
  await page.getByTestId('notif-bell').click();
  await expect(page.getByTestId('notif-item')).toContainText(title);
  await expect(page.getByTestId('notif-item')).toContainText('개정판'); // KIND_LABEL.REVISION

  // 알림함 페이지에서도 개정판 문구 확인 + 클릭 시 책 상세로 이동
  await page.goto('/notifications');
  const row = page.getByTestId('notif-row').filter({ hasText: title });
  await expect(row).toContainText('개정판이 나왔어요'); // KIND_SUFFIX.REVISION
  await row.click();
  await expect(page).toHaveURL(new RegExp(`/books/${bookId}`));
});
