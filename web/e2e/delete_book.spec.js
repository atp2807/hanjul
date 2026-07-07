import { expect, test } from '@playwright/test';

import { login, seedBook, seedPublishedBook, tokenFor } from './helpers.js';

// 미출판(DRAFT) + 가격 설정된 책을 시드.
function seedDraftBook(request, { authorEmail, title, price }) {
  return seedBook(request, { authorEmail, title, rawText: '# 1장\n\n본문.', price, publish: false });
}

// 판매 이력 없는 책 → 삭제(확인 다이얼로그 수락) → 스튜디오 목록에서 사라짐.
test('작가: 판매 이력 없는 책 삭제 → 목록에서 사라짐', async ({ page, request }) => {
  const email = 'del-author@x.com';
  const id = await seedDraftBook(request, { authorEmail: email, title: '삭제될책', price: 5000 });

  await login(page, email, '삭제작가');
  await page.goto(`/studio/${id}`);
  await expect(page.getByRole('heading', { name: '삭제될책' })).toBeVisible();

  page.on('dialog', (d) => d.accept()); // window.confirm 수락
  await page.getByRole('button', { name: '이 책 삭제' }).click();

  // 성공 → 스튜디오로 리다이렉트 + 목록에서 사라짐
  await expect(page).toHaveURL(/\/studio$/);
  await expect(page.getByText('삭제될책')).toHaveCount(0);
});

// 판매 이력 있는 책 → 삭제 시도 → 409, 에러 메시지 노출(삭제 안 됨).
test('작가: 판매 이력 있는 책 삭제 시도 → 409 에러 메시지', async ({ page, request }) => {
  const authorEmail = 'del-sold-author@x.com';
  const id = await seedPublishedBook(request, { authorEmail, title: '판매된책', price: 4000 });

  // 다른 사용자가 구매(데모결제) → 판매 이력 생성
  const buyer = { Authorization: `Bearer ${await tokenFor(request, 'del-buyer@x.com', '구매자')}` };
  const order = await (
    await request.post('/api/orders', {
      headers: buyer,
      data: { bookId: id, channel: 'SELF', withdrawalConsent: true },
    })
  ).json();
  await request.post(`/api/orders/${order.id}/confirm`, { headers: buyer, data: { pgTxId: 'demo' } });

  await login(page, authorEmail, '판매작가');
  await page.goto(`/studio/${id}`);
  await expect(page.getByRole('heading', { name: '판매된책' })).toBeVisible();

  page.on('dialog', (d) => d.accept());
  await page.getByRole('button', { name: '이 책 삭제' }).click();

  // 삭제 차단 — 에러 메시지 노출, 여전히 편집 페이지에 머무름
  await expect(page.getByText('판매 이력이 있어 삭제할 수 없어요. 출판 취소만 가능해요.')).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/studio/${id}$`));
});
