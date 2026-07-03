import { expect, test } from '@playwright/test';

import { login, seedPublishedBook } from './helpers.js';

async function tokenFor(request, email, name = '유저') {
  const res = await request.get(
    `/api/auth/test-login?email=${encodeURIComponent(email)}&name=${encodeURIComponent(name)}`,
    { maxRedirects: 0 },
  );
  return new URLSearchParams(res.headers()['location'].split('#')[1]).get('token');
}

// 한 명의 유저가 작가이자 독자 — 자기가 쓴 책은 스튜디오에만, 산 책은 서재에만.
// (다른 spec들은 작가/독자 이메일을 분리하지만 여기선 의도적으로 한 세션.)
test('겸업(작가+독자): 내 출판책=스튜디오 / 산 책=서재, 서로 섞이지 않음', async ({ page, request }) => {
  const aEmail = 'hybrid-a@x.com';
  const bEmail = 'hybrid-b@x.com';
  const myTitle = '겸업A가쓴책';
  const boughtTitle = '겸업B가쓴책';

  // A가 자기 책을 출판(작가 역할) + B가 다른 책을 출판(구매 대상 시드).
  await seedPublishedBook(request, { authorEmail: aEmail, title: myTitle, price: 7000 });
  const bBookId = await seedPublishedBook(request, { authorEmail: bEmail, title: boughtTitle, price: 4000 });

  // A로 로그인 — 로그아웃 없이 같은 세션에서 독자 역할까지 이어간다.
  await login(page, aEmail, '겸업A');

  // 독자 역할: 스토어에서 B의 책 구매(데모결제).
  await page.goto('/');
  await page.locator('a', { hasText: boughtTitle }).first().click();
  await page.getByTestId('withdrawal-consent').locator('input[type="checkbox"]').check();
  await page.getByRole('button', { name: '구매' }).click();
  await expect(page).toHaveURL(/\/read\//);

  // 서재: 산 책(B)만 있고 자기가 쓴 책(A)은 없다.
  await page.goto('/library');
  await expect(page.getByText(boughtTitle).first()).toBeVisible();
  await expect(page.getByText(myTitle)).toHaveCount(0);

  // 스튜디오: 자기가 쓴 책(A)만 있고 산 책(B)은 없다.
  await page.goto('/studio');
  await expect(page.getByText(myTitle).first()).toBeVisible();
  await expect(page.getByText(boughtTitle)).toHaveCount(0);

  // B가 연 캠페인에 A가 서평단으로 신청(같은 세션, 독자 역할 연장).
  const bAuth = { Authorization: `Bearer ${await tokenFor(request, bEmail, 'B작가')}` };
  const camp = await (
    await request.post('/api/campaigns', {
      headers: bAuth,
      data: { bookId: bBookId, slots: 1, reviewDays: 14, minChars: 5 },
    })
  ).json();
  await page.goto(`/campaigns/${camp.campaignId}`);
  await page.getByRole('button', { name: '리뷰어 신청하기' }).click();
  await expect(page.getByText('신청 완료')).toBeVisible();
});
