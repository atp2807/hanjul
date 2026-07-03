import { expect, test } from '@playwright/test';

import { login, seedPublishedBook } from './helpers.js';

// 작가 정산·출금 전 여정: 출판 → 독자 구매(데모결제) → 스튜디오 매출 집계 → 계좌 등록 → 출금 신청 → 내역 확인
test('작가: 매출 집계→계좌 등록→출금 신청', async ({ page, request }) => {
  const authorEmail = 'payout-author@x.com';
  const title = '출금여정책';
  await seedPublishedBook(request, { authorEmail, title, price: 10000 });

  // 독자가 구매(데모결제) — 판매 1건 발생 → 정산 스냅샷 생성
  await login(page, 'payout-buyer@x.com', '출금구매자');
  await page.goto('/');
  await page.locator('a', { hasText: title }).first().click();
  await page.getByTestId('withdrawal-consent').locator('input[type="checkbox"]').check();
  await page.getByRole('button', { name: '구매' }).click();
  await expect(page).toHaveURL(/\/read\/[0-9a-f-]+$/);
  await page.getByRole('button', { name: '로그아웃' }).click();

  // 작가: 스튜디오에서 매출 집계 확인
  await login(page, authorEmail, '출금작가');
  await page.goto('/studio');
  await expect(page.getByText('판매 부수')).toBeVisible();
  await expect(page.getByText('총 매출')).toBeVisible();
  await expect(page.getByText('10,000원').first()).toBeVisible(); // 총 매출
  await expect(page.getByText('1권').first()).toBeVisible(); // 판매 부수

  // 정산·출금: 계좌 미등록 → 등록 폼 노출
  await page.goto('/settlement');
  await expect(page.getByRole('button', { name: '계좌 저장' })).toBeVisible();

  // 계좌 등록
  await page.getByPlaceholder('홍길동').fill('출금작가');
  await page.getByPlaceholder('국민은행').fill('국민은행');
  await page.getByPlaceholder('숫자만').fill('123456789012');
  await page.getByRole('button', { name: '계좌 저장' }).click();
  await expect(page.getByText('국민은행').first()).toBeVisible(); // 저장된 계좌 요약 노출

  // 출금 가능액 > 0 (10,000원 판매 → 3.3% 원천징수 후 6,769원)
  await expect(page.getByText('6,769원')).toBeVisible();
  const withdrawBtn = page.getByRole('button', { name: '출금 신청' });
  await expect(withdrawBtn).toBeEnabled();

  // 출금 신청 → 성공 메시지 + 내역에 '신청됨'
  await withdrawBtn.click();
  await expect(page.getByText('출금을 신청했어요. 검토 후 지급됩니다.')).toBeVisible();
  await expect(page.getByText('신청됨')).toBeVisible();
});
